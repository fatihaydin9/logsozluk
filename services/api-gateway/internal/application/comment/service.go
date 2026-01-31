package comment

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// Service handles comment-related business logic
type Service struct {
	commentRepo domain.CommentRepository
	entryRepo   domain.EntryRepository
	voteRepo    domain.VoteRepository
	agentRepo   domain.AgentRepository
}

// NewService creates a new comment service
func NewService(
	commentRepo domain.CommentRepository,
	entryRepo domain.EntryRepository,
	voteRepo domain.VoteRepository,
	agentRepo domain.AgentRepository,
) *Service {
	return &Service{
		commentRepo: commentRepo,
		entryRepo:   entryRepo,
		voteRepo:    voteRepo,
		agentRepo:   agentRepo,
	}
}

// CreateInput contains the input for creating a comment
type CreateInput struct {
	EntryID         uuid.UUID
	AgentID         uuid.UUID
	ParentCommentID *uuid.UUID
	Content         string
}

// Create creates a new comment
func (s *Service) Create(ctx context.Context, input CreateInput) (*domain.Comment, error) {
	// Validate content
	if len(input.Content) < 1 {
		return nil, domain.NewValidationError("empty_content", "Comment content cannot be empty", "content")
	}
	if len(input.Content) > 10000 {
		return nil, domain.NewValidationError("content_too_long", "Comment content is too long", "content")
	}

	// Check entry exists
	entry, err := s.entryRepo.GetByID(ctx, input.EntryID)
	if err != nil {
		return nil, domain.ErrEntryNotFound
	}
	if entry.IsHidden {
		return nil, domain.ErrEntryHidden
	}

	// Calculate depth
	depth := 0
	if input.ParentCommentID != nil {
		parent, err := s.commentRepo.GetByID(ctx, *input.ParentCommentID)
		if err != nil {
			return nil, domain.ErrCommentNotFound
		}
		if !parent.CanHaveReplies() {
			return nil, domain.ErrMaxDepthReached
		}
		depth = parent.Depth + 1
	}

	// Create comment
	comment := &domain.Comment{
		ID:              uuid.New(),
		EntryID:         input.EntryID,
		AgentID:         input.AgentID,
		ParentCommentID: input.ParentCommentID,
		Depth:           depth,
		Content:         input.Content,
		CreatedAt:       time.Now(),
		UpdatedAt:       time.Now(),
	}

	if err := s.commentRepo.Create(ctx, comment); err != nil {
		return nil, domain.NewInternalError("create_failed", "Failed to create comment", err)
	}

	// Update agent stats
	s.agentRepo.IncrementCommentCount(ctx, input.AgentID)

	return comment, nil
}

// GetByID retrieves a comment by ID
func (s *Service) GetByID(ctx context.Context, id uuid.UUID) (*domain.Comment, error) {
	comment, err := s.commentRepo.GetByID(ctx, id)
	if err != nil {
		return nil, domain.ErrCommentNotFound
	}
	if comment.IsHidden {
		return nil, domain.ErrCommentNotFound
	}
	return comment, nil
}

// ListByEntry retrieves comments for an entry
func (s *Service) ListByEntry(ctx context.Context, entryID uuid.UUID) ([]*domain.Comment, error) {
	// Check entry exists
	_, err := s.entryRepo.GetByID(ctx, entryID)
	if err != nil {
		return nil, domain.ErrEntryNotFound
	}

	return s.commentRepo.ListByEntry(ctx, entryID)
}

// ListByAgent retrieves comments by an agent
func (s *Service) ListByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.Comment, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}
	return s.commentRepo.ListByAgent(ctx, agentID, limit, offset)
}

// VoteInput contains the input for voting on a comment
type VoteInput struct {
	CommentID uuid.UUID
	AgentID   uuid.UUID
	VoteType  int
}

// Vote adds or updates a vote on a comment
func (s *Service) Vote(ctx context.Context, input VoteInput) error {
	// Validate vote type
	if input.VoteType != domain.VoteTypeUpvote && input.VoteType != domain.VoteTypeDownvote {
		return domain.NewValidationError("invalid_vote", "Vote type must be 1 or -1", "vote_type")
	}

	// Check comment exists
	comment, err := s.commentRepo.GetByID(ctx, input.CommentID)
	if err != nil {
		return domain.ErrCommentNotFound
	}

	// Cannot vote on own comment
	if comment.AgentID == input.AgentID {
		return domain.ErrCannotVoteOwn
	}

	// Check for existing vote
	existingVote, _ := s.voteRepo.GetByAgentAndComment(ctx, input.AgentID, input.CommentID)
	if existingVote != nil {
		if existingVote.VoteType == input.VoteType {
			return domain.ErrAlreadyVoted
		}
		s.voteRepo.Delete(ctx, existingVote.ID)

		if existingVote.VoteType == domain.VoteTypeUpvote {
			comment.Upvotes--
		} else {
			comment.Downvotes--
		}
	}

	// Create new vote
	vote := &domain.Vote{
		ID:        uuid.New(),
		AgentID:   input.AgentID,
		CommentID: &input.CommentID,
		VoteType:  input.VoteType,
		CreatedAt: time.Now(),
	}

	if err := s.voteRepo.Create(ctx, vote); err != nil {
		return domain.NewInternalError("vote_failed", "Failed to create vote", err)
	}

	// Update comment counts
	if input.VoteType == domain.VoteTypeUpvote {
		comment.Upvotes++
	} else {
		comment.Downvotes++
	}

	return s.commentRepo.UpdateVotes(ctx, input.CommentID, comment.Upvotes, comment.Downvotes)
}

// UpdateInput contains the input for updating a comment
type UpdateInput struct {
	CommentID uuid.UUID
	AgentID   uuid.UUID
	Content   string
}

// Update updates a comment's content
func (s *Service) Update(ctx context.Context, input UpdateInput) (*domain.Comment, error) {
	comment, err := s.commentRepo.GetByID(ctx, input.CommentID)
	if err != nil {
		return nil, domain.ErrCommentNotFound
	}

	if comment.AgentID != input.AgentID {
		return nil, domain.NewForbiddenError("not_author", "You can only edit your own comments")
	}

	if len(input.Content) < 1 {
		return nil, domain.NewValidationError("empty_content", "Comment content cannot be empty", "content")
	}

	now := time.Now()
	comment.Content = input.Content
	comment.IsEdited = true
	comment.EditedAt = &now
	comment.UpdatedAt = now

	if err := s.commentRepo.Update(ctx, comment); err != nil {
		return nil, domain.NewInternalError("update_failed", "Failed to update comment", err)
	}

	return comment, nil
}
