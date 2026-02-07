package task

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// EntryService — SSOT for entry creation/voting (implemented by entry.Service)
type EntryService interface {
	Create(ctx context.Context, input EntryCreateInput) (*domain.Entry, error)
	Vote(ctx context.Context, input EntryVoteInput) error
	GetByAgentAndTopic(ctx context.Context, agentID, topicID uuid.UUID) (*domain.Entry, error)
}

// EntryCreateInput mirrors entry.CreateInput to avoid circular imports
type EntryCreateInput struct {
	TopicID uuid.UUID
	AgentID uuid.UUID
	Content string
	TaskID  *uuid.UUID
}

// EntryVoteInput mirrors entry.VoteInput
type EntryVoteInput struct {
	EntryID  uuid.UUID
	AgentID  uuid.UUID
	VoteType int
}

// CommentService — SSOT for comment creation (implemented by comment.Service)
type CommentService interface {
	Create(ctx context.Context, input CommentCreateInput) (*domain.Comment, error)
}

// CommentCreateInput mirrors comment.CreateInput
type CommentCreateInput struct {
	EntryID         uuid.UUID
	AgentID         uuid.UUID
	ParentCommentID *uuid.UUID
	Content         string
}

// Service handles task-related business logic
type Service struct {
	taskRepo       domain.TaskRepository
	topicRepo      domain.TopicRepository
	entryService   EntryService
	commentService CommentService
}

// NewService creates a new task service
func NewService(taskRepo domain.TaskRepository, topicRepo domain.TopicRepository, entryService EntryService, commentService CommentService) *Service {
	return &Service{
		taskRepo:       taskRepo,
		topicRepo:      topicRepo,
		entryService:   entryService,
		commentService: commentService,
	}
}

// GetByID retrieves a task by ID
func (s *Service) GetByID(ctx context.Context, id uuid.UUID) (*domain.Task, error) {
	task, err := s.taskRepo.GetByIDWithRelations(ctx, id)
	if err != nil {
		return nil, domain.ErrTaskNotFound
	}
	return task, nil
}

// ListPending retrieves pending tasks
func (s *Service) ListPending(ctx context.Context, limit int) ([]*domain.Task, error) {
	if limit <= 0 || limit > 50 {
		limit = 10
	}
	return s.taskRepo.ListPending(ctx, limit)
}

// ListForAgent retrieves pending tasks assigned to a specific agent (for SDK/external agents)
func (s *Service) ListForAgent(ctx context.Context, agentID uuid.UUID, limit int) ([]*domain.Task, error) {
	if limit <= 0 || limit > 50 {
		limit = 10
	}
	return s.taskRepo.ListPendingForAgent(ctx, agentID, limit)
}

// ListByAgent retrieves tasks assigned to an agent
func (s *Service) ListByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.Task, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}
	return s.taskRepo.ListByAgent(ctx, agentID, limit, offset)
}

// Claim claims a task for an agent
func (s *Service) Claim(ctx context.Context, taskID, agentID uuid.UUID) (*domain.Task, error) {
	task, err := s.taskRepo.GetByID(ctx, taskID)
	if err != nil {
		return nil, domain.ErrTaskNotFound
	}

	if !task.CanBeClaimed() {
		if task.IsExpired() {
			return nil, domain.ErrTaskExpired
		}
		return nil, domain.ErrTaskAlreadyClaimed
	}

	if err := s.taskRepo.Claim(ctx, taskID, agentID); err != nil {
		// Check if it's a known domain error (e.g., already claimed by another agent)
		if err == domain.ErrTaskAlreadyClaimed {
			return nil, err
		}
		return nil, domain.NewInternalError("claim_failed", "Failed to claim task", err)
	}

	return s.taskRepo.GetByIDWithRelations(ctx, taskID)
}

// CompleteInput contains the input for completing a task
type CompleteInput struct {
	TaskID       uuid.UUID
	AgentID      uuid.UUID
	EntryContent string
	VoteType     *int
}

// Complete completes a task with a result
func (s *Service) Complete(ctx context.Context, input CompleteInput) (*domain.Task, error) {
	task, err := s.taskRepo.GetByID(ctx, input.TaskID)
	if err != nil {
		return nil, domain.ErrTaskNotFound
	}

	if !task.IsAssignedTo(input.AgentID) {
		return nil, domain.ErrTaskNotAssigned
	}

	if task.IsCompleted() {
		return nil, domain.NewConflictError("already_completed", "Task is already completed")
	}

	var resultEntryID *uuid.UUID
	var resultCommentID *uuid.UUID

	switch task.TaskType {
	case domain.TaskTypeWriteEntry:
		if input.EntryContent == "" {
			return nil, domain.NewValidationError("missing_content", "Entry content is required", "content")
		}
		if task.TopicID == nil {
			return nil, domain.NewValidationError("missing_topic", "Topic ID is required", "topic_id")
		}

		// SSOT: delegate to entryService.Create() — same path as system agents
		entry, err := s.entryService.Create(ctx, EntryCreateInput{
			TopicID: *task.TopicID,
			AgentID: input.AgentID,
			Content: input.EntryContent,
			TaskID:  &task.ID,
		})
		if err != nil {
			// Duplicate → mark task completed without new entry
			if isDuplicateError(err) {
				existing, _ := s.entryService.GetByAgentAndTopic(ctx, input.AgentID, *task.TopicID)
				var existingID *uuid.UUID
				if existing != nil {
					existingID = &existing.ID
				}
				if err := s.taskRepo.Complete(ctx, task.ID, existingID, nil); err != nil {
					return nil, domain.NewInternalError("complete_failed", "Failed to complete task", err)
				}
				return s.taskRepo.GetByIDWithRelations(ctx, task.ID)
			}
			return nil, err
		}
		resultEntryID = &entry.ID

	case domain.TaskTypeCreateTopic:
		if input.EntryContent == "" {
			return nil, domain.NewValidationError("missing_content", "Entry content is required for topic creation", "content")
		}

		// Extract topic title from prompt context
		var promptCtx map[string]interface{}
		if err := json.Unmarshal(task.PromptContext, &promptCtx); err != nil {
			return nil, domain.NewInternalError("invalid_context", "Invalid prompt context", err)
		}

		topicTitle, ok := promptCtx["event_title"].(string)
		if !ok || topicTitle == "" {
			return nil, domain.NewValidationError("missing_title", "Topic title is required", "event_title")
		}

		// Generate slug from title
		slug := domain.GenerateSlug(topicTitle)

		// Check if topic with this slug already exists
		existingTopic, err := s.topicRepo.GetBySlug(ctx, slug)
		var targetTopicID uuid.UUID
		if err == nil && existingTopic != nil {
			targetTopicID = existingTopic.ID
		} else {
			// Create new topic
			category := "general"
			if cat, ok := promptCtx["category"].(string); ok && cat != "" {
				category = cat
			}

			var phase *string
			if p, ok := promptCtx["phase"].(string); ok && p != "" {
				phase = &p
			}

			newTopic := &domain.Topic{
				ID:              uuid.New(),
				Slug:            slug,
				Title:           topicTitle,
				Category:        category,
				CreatedBy:       &input.AgentID,
				VirtualDayPhase: phase,
				CreatedAt:       time.Now(),
				UpdatedAt:       time.Now(),
			}

			if err := s.topicRepo.Create(ctx, newTopic); err != nil {
				return nil, domain.NewInternalError("topic_failed", "Failed to create topic", err)
			}
			targetTopicID = newTopic.ID
		}

		// SSOT: delegate entry creation to entryService
		entry, err := s.entryService.Create(ctx, EntryCreateInput{
			TopicID: targetTopicID,
			AgentID: input.AgentID,
			Content: input.EntryContent,
			TaskID:  &task.ID,
		})
		if err != nil {
			if isDuplicateError(err) {
				existing, _ := s.entryService.GetByAgentAndTopic(ctx, input.AgentID, targetTopicID)
				var existingID *uuid.UUID
				if existing != nil {
					existingID = &existing.ID
				}
				if err := s.taskRepo.Complete(ctx, task.ID, existingID, nil); err != nil {
					return nil, domain.NewInternalError("complete_failed", "Failed to complete task", err)
				}
				return s.taskRepo.GetByIDWithRelations(ctx, task.ID)
			}
			return nil, err
		}
		resultEntryID = &entry.ID

	case domain.TaskTypeWriteComment:
		if input.EntryContent == "" {
			return nil, domain.NewValidationError("missing_content", "Comment content is required", "content")
		}
		if task.EntryID == nil {
			return nil, domain.NewValidationError("missing_entry", "Entry ID is required for comment task", "entry_id")
		}

		// SSOT: delegate to commentService.Create() — same path as system agents
		comment, err := s.commentService.Create(ctx, CommentCreateInput{
			EntryID: *task.EntryID,
			AgentID: input.AgentID,
			Content: input.EntryContent,
		})
		if err != nil {
			// Duplicate or self-comment → mark task completed gracefully
			if isDuplicateError(err) || isConflictError(err) {
				if err := s.taskRepo.Complete(ctx, task.ID, nil, nil); err != nil {
					return nil, domain.NewInternalError("complete_failed", "Failed to complete task", err)
				}
				return s.taskRepo.GetByIDWithRelations(ctx, task.ID)
			}
			return nil, err
		}
		resultCommentID = &comment.ID

	case domain.TaskTypeVote:
		if input.VoteType == nil {
			return nil, domain.NewValidationError("missing_vote", "Vote type is required", "vote_type")
		}

		// SSOT: delegate to entryService.Vote() — same path as direct API votes
		if task.EntryID != nil {
			err := s.entryService.Vote(ctx, EntryVoteInput{
				EntryID:  *task.EntryID,
				AgentID:  input.AgentID,
				VoteType: *input.VoteType,
			})
			if err != nil {
				// Already voted or own entry → not fatal for task completion
				if !errors.Is(err, domain.ErrAlreadyVoted) && !errors.Is(err, domain.ErrCannotVoteOwn) {
					return nil, err
				}
			}
		}
	}

	if err := s.taskRepo.Complete(ctx, task.ID, resultEntryID, resultCommentID); err != nil {
		return nil, domain.NewInternalError("complete_failed", "Failed to complete task", err)
	}

	return s.taskRepo.GetByIDWithRelations(ctx, task.ID)
}

// isDuplicateError checks if the error is a duplicate/conflict domain error
func isDuplicateError(err error) bool {
	var domainErr *domain.Error
	if errors.As(err, &domainErr) {
		return domainErr.Category == domain.ErrCategoryConflict && domainErr.Code == "duplicate_entry"
	}
	return false
}

// isConflictError checks if the error is any conflict domain error
func isConflictError(err error) bool {
	var domainErr *domain.Error
	if errors.As(err, &domainErr) {
		return domainErr.Category == domain.ErrCategoryConflict
	}
	return false
}

// CreateInput contains the input for creating a task (internal/admin use)
type CreateInput struct {
	TaskType      string
	TopicID       *uuid.UUID
	EntryID       *uuid.UUID
	PromptContext map[string]interface{}
	Priority      int
	ExpiresIn     time.Duration
}

// Create creates a new task (for agenda-engine)
func (s *Service) Create(ctx context.Context, input CreateInput) (*domain.Task, error) {
	var promptContextJSON json.RawMessage
	if input.PromptContext != nil {
		data, _ := json.Marshal(input.PromptContext)
		promptContextJSON = data
	}

	var expiresAt *time.Time
	if input.ExpiresIn > 0 {
		t := time.Now().Add(input.ExpiresIn)
		expiresAt = &t
	}

	task := &domain.Task{
		ID:            uuid.New(),
		TaskType:      input.TaskType,
		TopicID:       input.TopicID,
		EntryID:       input.EntryID,
		PromptContext: promptContextJSON,
		Priority:      input.Priority,
		Status:        domain.TaskStatusPending,
		ExpiresAt:     expiresAt,
		CreatedAt:     time.Now(),
	}

	if err := s.taskRepo.Create(ctx, task); err != nil {
		return nil, domain.NewInternalError("create_failed", "Failed to create task", err)
	}

	return task, nil
}
