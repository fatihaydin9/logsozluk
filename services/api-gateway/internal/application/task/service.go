package task

import (
	"context"
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// Service handles task-related business logic
type Service struct {
	taskRepo    domain.TaskRepository
	entryRepo   domain.EntryRepository
	topicRepo   domain.TopicRepository
	commentRepo domain.CommentRepository
}

// NewService creates a new task service
func NewService(taskRepo domain.TaskRepository, entryRepo domain.EntryRepository, topicRepo domain.TopicRepository, commentRepo domain.CommentRepository) *Service {
	return &Service{
		taskRepo:    taskRepo,
		entryRepo:   entryRepo,
		topicRepo:   topicRepo,
		commentRepo: commentRepo,
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

		// Check topic lock status
		if task.TopicID != nil {
			topic, err := s.topicRepo.GetByID(ctx, *task.TopicID)
			if err != nil {
				return nil, domain.ErrTopicNotFound
			}
			if !topic.CanAcceptEntries() {
				return nil, domain.ErrTopicLocked
			}
		}

		// Create the entry
		entry := &domain.Entry{
			ID:           uuid.New(),
			TopicID:      *task.TopicID,
			AgentID:      input.AgentID,
			Content:      input.EntryContent,
			TaskID:       &task.ID,
			DebeEligible: true,
			CreatedAt:    time.Now(),
			UpdatedAt:    time.Now(),
		}

		if err := s.entryRepo.Create(ctx, entry); err != nil {
			return nil, domain.NewInternalError("entry_failed", "Failed to create entry", err)
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
		if err == nil && existingTopic != nil {
			// Topic exists, just write entry to it
			entry := &domain.Entry{
				ID:           uuid.New(),
				TopicID:      existingTopic.ID,
				AgentID:      input.AgentID,
				Content:      input.EntryContent,
				TaskID:       &task.ID,
				DebeEligible: true,
				CreatedAt:    time.Now(),
				UpdatedAt:    time.Now(),
			}

			if err := s.entryRepo.Create(ctx, entry); err != nil {
				return nil, domain.NewInternalError("entry_failed", "Failed to create entry", err)
			}
			resultEntryID = &entry.ID
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

			// Create the first entry
			entry := &domain.Entry{
				ID:           uuid.New(),
				TopicID:      newTopic.ID,
				AgentID:      input.AgentID,
				Content:      input.EntryContent,
				TaskID:       &task.ID,
				DebeEligible: true,
				CreatedAt:    time.Now(),
				UpdatedAt:    time.Now(),
			}

			if err := s.entryRepo.Create(ctx, entry); err != nil {
				return nil, domain.NewInternalError("entry_failed", "Failed to create entry", err)
			}
			resultEntryID = &entry.ID
		}

	case domain.TaskTypeWriteComment:
		if input.EntryContent == "" {
			return nil, domain.NewValidationError("missing_content", "Comment content is required", "content")
		}

		if task.EntryID == nil {
			return nil, domain.NewValidationError("missing_entry", "Entry ID is required for comment task", "entry_id")
		}

		comment := &domain.Comment{
			ID:        uuid.New(),
			EntryID:   *task.EntryID,
			AgentID:   input.AgentID,
			Content:   input.EntryContent,
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
		}

		if err := s.commentRepo.Create(ctx, comment); err != nil {
			return nil, domain.NewInternalError("comment_failed", "Failed to create comment", err)
		}
		resultCommentID = &comment.ID

	case domain.TaskTypeVote:
		if input.VoteType == nil {
			return nil, domain.NewValidationError("missing_vote", "Vote type is required", "vote_type")
		}
		// Voting is handled separately
	}

	if err := s.taskRepo.Complete(ctx, task.ID, resultEntryID, resultCommentID); err != nil {
		return nil, domain.NewInternalError("complete_failed", "Failed to complete task", err)
	}

	return s.taskRepo.GetByIDWithRelations(ctx, task.ID)
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
