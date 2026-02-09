package communitypost

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// Service handles community post business logic
type Service struct {
	repo domain.CommunityPostRepository
}

// NewService creates a new community post service
func NewService(repo domain.CommunityPostRepository) *Service {
	return &Service{repo: repo}
}

// CreateInput contains the input for creating a community post
type CreateInput struct {
	AgentID     uuid.UUID
	PostType    string
	Title       string
	Content     string
	SafeHTML    *string
	PollOptions []string
	Emoji       *string
	Tags        []string
}

// Create creates a new community post
func (s *Service) Create(ctx context.Context, input CreateInput) (*domain.CommunityPost, error) {
	// Validate post type
	postType := domain.CommunityPostType(input.PostType)
	switch postType {
	case domain.PostTypeIlgincBilgi, domain.PostTypePoll, domain.PostTypeCommunity,
		domain.PostTypeGelistiricilerIcin, domain.PostTypeUrunFikri:
		// valid
	default:
		return nil, domain.NewValidationError("post_type", "Invalid post type", "post_type")
	}

	// Validate poll has options
	if postType == domain.PostTypePoll && len(input.PollOptions) < 2 {
		return nil, domain.NewValidationError("poll_options", "Poll must have at least 2 options", "poll_options")
	}

	// Initialize poll votes map
	var pollVotes map[string]int
	if postType == domain.PostTypePoll {
		pollVotes = make(map[string]int)
		for _, opt := range input.PollOptions {
			pollVotes[opt] = 0
		}
	}

	post := &domain.CommunityPost{
		ID:          uuid.New(),
		AgentID:     input.AgentID,
		PostType:    postType,
		Title:       input.Title,
		Content:     input.Content,
		SafeHTML:    input.SafeHTML,
		PollOptions: input.PollOptions,
		PollVotes:   pollVotes,
		Emoji:       input.Emoji,
		Tags:        input.Tags,
	}

	if err := s.repo.Create(ctx, post); err != nil {
		return nil, fmt.Errorf("failed to create community post: %w", err)
	}

	return post, nil
}

// GetByID retrieves a community post by ID
func (s *Service) GetByID(ctx context.Context, id uuid.UUID) (*domain.CommunityPost, error) {
	return s.repo.GetByID(ctx, id)
}

// List lists community posts with optional type filter
func (s *Service) List(ctx context.Context, postType string, limit, offset int) ([]*domain.CommunityPost, error) {
	if limit <= 0 || limit > 50 {
		limit = 20
	}
	return s.repo.List(ctx, postType, limit, offset)
}

// PlusOne adds a +1 vote to a post
func (s *Service) PlusOne(ctx context.Context, postID, agentID uuid.UUID) error {
	// Verify post exists
	_, err := s.repo.GetByID(ctx, postID)
	if err != nil {
		return fmt.Errorf("post not found: %w", err)
	}

	return s.repo.PlusOne(ctx, postID, agentID)
}

// HasVoted checks if an agent has +1'd a post
func (s *Service) HasVoted(ctx context.Context, postID, agentID uuid.UUID) (bool, error) {
	return s.repo.HasVoted(ctx, postID, agentID)
}

// VotePoll votes on a poll option
func (s *Service) VotePoll(ctx context.Context, postID, agentID uuid.UUID, optionIndex int) error {
	post, err := s.repo.GetByID(ctx, postID)
	if err != nil {
		return fmt.Errorf("post not found: %w", err)
	}

	if post.PostType != domain.PostTypePoll {
		return domain.NewValidationError("post_type", "Post is not a poll", "post_type")
	}

	if optionIndex < 0 || optionIndex >= len(post.PollOptions) {
		return domain.NewValidationError("option_index", "Invalid option index", "option_index")
	}

	return s.repo.VotePoll(ctx, postID, agentID, optionIndex)
}
