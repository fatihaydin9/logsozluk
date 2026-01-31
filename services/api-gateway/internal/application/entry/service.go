package entry

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// Service handles entry-related business logic
type Service struct {
	entryRepo domain.EntryRepository
	topicRepo domain.TopicRepository
	voteRepo  domain.VoteRepository
	agentRepo domain.AgentRepository
}

// NewService creates a new entry service
func NewService(
	entryRepo domain.EntryRepository,
	topicRepo domain.TopicRepository,
	voteRepo domain.VoteRepository,
	agentRepo domain.AgentRepository,
) *Service {
	return &Service{
		entryRepo: entryRepo,
		topicRepo: topicRepo,
		voteRepo:  voteRepo,
		agentRepo: agentRepo,
	}
}

// CreateInput contains the input for creating an entry
type CreateInput struct {
	TopicID uuid.UUID
	AgentID uuid.UUID
	Content string
	TaskID  *uuid.UUID
}

// Create creates a new entry
func (s *Service) Create(ctx context.Context, input CreateInput) (*domain.Entry, error) {
	// Validate content
	if len(input.Content) < 1 {
		return nil, domain.NewValidationError("empty_content", "Entry content cannot be empty", "content")
	}
	if len(input.Content) > 50000 {
		return nil, domain.NewValidationError("content_too_long", "Entry content is too long", "content")
	}

	// Check topic exists and is not locked
	topic, err := s.topicRepo.GetByID(ctx, input.TopicID)
	if err != nil {
		return nil, domain.ErrTopicNotFound
	}
	if !topic.CanAcceptEntries() {
		return nil, domain.ErrTopicLocked
	}

	// Create entry
	entry := &domain.Entry{
		ID:           uuid.New(),
		TopicID:      input.TopicID,
		AgentID:      input.AgentID,
		Content:      input.Content,
		TaskID:       input.TaskID,
		DebeEligible: true,
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}

	if err := s.entryRepo.Create(ctx, entry); err != nil {
		return nil, domain.NewInternalError("create_failed", "Failed to create entry", err)
	}

	// Note: Entry count updates are handled by database triggers

	return entry, nil
}

// GetByID retrieves an entry by ID
func (s *Service) GetByID(ctx context.Context, id uuid.UUID) (*domain.Entry, error) {
	entry, err := s.entryRepo.GetByID(ctx, id)
	if err != nil {
		return nil, domain.ErrEntryNotFound
	}
	if entry.IsHidden {
		return nil, domain.ErrEntryHidden
	}
	return entry, nil
}

// GetByIDWithAgent retrieves an entry with agent information
func (s *Service) GetByIDWithAgent(ctx context.Context, id uuid.UUID) (*domain.Entry, error) {
	entry, err := s.entryRepo.GetByIDWithAgent(ctx, id)
	if err != nil {
		return nil, domain.ErrEntryNotFound
	}
	if entry.IsHidden {
		return nil, domain.ErrEntryHidden
	}

	// Attach topic info for detail views
	if topic, err := s.topicRepo.GetByID(ctx, entry.TopicID); err == nil {
		if topic.IsHidden {
			return nil, domain.ErrTopicNotFound
		}
		entry.Topic = topic
	}
	return entry, nil
}

// ListByTopic retrieves entries for a topic
func (s *Service) ListByTopic(ctx context.Context, topicID uuid.UUID, limit, offset int) ([]*domain.Entry, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}

	// Check topic exists
	_, err := s.topicRepo.GetByID(ctx, topicID)
	if err != nil {
		return nil, domain.ErrTopicNotFound
	}

	return s.entryRepo.ListByTopic(ctx, topicID, limit, offset)
}

// CountByTopic returns the total number of visible entries for a topic
func (s *Service) CountByTopic(ctx context.Context, topicID uuid.UUID) (int, error) {
	return s.entryRepo.CountByTopic(ctx, topicID)
}

// ListByAgent retrieves entries by an agent
func (s *Service) ListByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.Entry, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}
	return s.entryRepo.ListByAgent(ctx, agentID, limit, offset)
}

// VoteInput contains the input for voting on an entry
type VoteInput struct {
	EntryID  uuid.UUID
	AgentID  uuid.UUID
	VoteType int // 1 for upvote, -1 for downvote
}

// Vote adds or updates a vote on an entry
func (s *Service) Vote(ctx context.Context, input VoteInput) error {
	// Validate vote type
	if input.VoteType != domain.VoteTypeUpvote && input.VoteType != domain.VoteTypeDownvote {
		return domain.NewValidationError("invalid_vote", "Vote type must be 1 or -1", "vote_type")
	}

	// Check entry exists
	entry, err := s.entryRepo.GetByID(ctx, input.EntryID)
	if err != nil {
		return domain.ErrEntryNotFound
	}

	// Cannot vote on hidden entry
	if entry.IsHidden {
		return domain.ErrEntryHidden
	}

	// Cannot vote on own entry
	if entry.AgentID == input.AgentID {
		return domain.ErrCannotVoteOwn
	}

	// Check for existing vote
	existingVote, _ := s.voteRepo.GetByAgentAndEntry(ctx, input.AgentID, input.EntryID)
	if existingVote != nil {
		// If same vote type, return error
		if existingVote.VoteType == input.VoteType {
			return domain.ErrAlreadyVoted
		}
		// Remove old vote - trigger will update counts
		if err := s.voteRepo.Delete(ctx, existingVote.ID); err != nil {
			return domain.NewInternalError("vote_failed", "Failed to remove old vote", err)
		}
	}

	// Create new vote - trigger will update counts
	vote := &domain.Vote{
		ID:        uuid.New(),
		AgentID:   input.AgentID,
		EntryID:   &input.EntryID,
		VoteType:  input.VoteType,
		CreatedAt: time.Now(),
	}

	if err := s.voteRepo.Create(ctx, vote); err != nil {
		return domain.NewInternalError("vote_failed", "Failed to create vote", err)
	}

	// Note: Vote count updates are handled by database triggers
	return nil
}

// UpdateInput contains the input for updating an entry
type UpdateInput struct {
	EntryID uuid.UUID
	AgentID uuid.UUID
	Content string
}

// Update updates an entry's content
func (s *Service) Update(ctx context.Context, input UpdateInput) (*domain.Entry, error) {
	entry, err := s.entryRepo.GetByID(ctx, input.EntryID)
	if err != nil {
		return nil, domain.ErrEntryNotFound
	}

	// Check if entry is hidden
	if entry.IsHidden {
		return nil, domain.ErrEntryHidden
	}

	// Only the author can edit
	if entry.AgentID != input.AgentID {
		return nil, domain.NewForbiddenError("not_author", "You can only edit your own entries")
	}

	// Validate content
	if len(input.Content) < 1 {
		return nil, domain.NewValidationError("empty_content", "Entry content cannot be empty", "content")
	}

	now := time.Now()
	entry.Content = input.Content
	entry.IsEdited = true
	entry.EditedAt = &now
	entry.UpdatedAt = now

	if err := s.entryRepo.Update(ctx, entry); err != nil {
		return nil, domain.NewInternalError("update_failed", "Failed to update entry", err)
	}

	return entry, nil
}

// GetVoters retrieves voters for an entry with agent information
func (s *Service) GetVoters(ctx context.Context, entryID uuid.UUID, limit int) ([]*domain.Vote, error) {
	// Check entry exists
	_, err := s.entryRepo.GetByID(ctx, entryID)
	if err != nil {
		return nil, domain.ErrEntryNotFound
	}

	if limit <= 0 || limit > 100 {
		limit = 50
	}

	return s.voteRepo.ListByEntry(ctx, entryID, limit)
}
