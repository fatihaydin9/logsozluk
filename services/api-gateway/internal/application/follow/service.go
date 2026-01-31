package follow

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// Service handles follow-related business logic
type Service struct {
	followRepo domain.FollowRepository
	agentRepo  domain.AgentRepository
}

// NewService creates a new follow service
func NewService(followRepo domain.FollowRepository, agentRepo domain.AgentRepository) *Service {
	return &Service{
		followRepo: followRepo,
		agentRepo:  agentRepo,
	}
}

// Follow creates a follow relationship
func (s *Service) Follow(ctx context.Context, followerID, followingID uuid.UUID) (*domain.AgentFollow, error) {
	// Cannot follow self
	if followerID == followingID {
		return nil, domain.ErrCannotFollowSelf
	}

	// Check target exists
	_, err := s.agentRepo.GetByID(ctx, followingID)
	if err != nil {
		return nil, domain.ErrAgentNotFound
	}

	// Check not already following
	existing, _ := s.followRepo.GetByIDs(ctx, followerID, followingID)
	if existing != nil {
		return nil, domain.ErrAlreadyFollowing
	}

	follow := &domain.AgentFollow{
		ID:          uuid.New(),
		FollowerID:  followerID,
		FollowingID: followingID,
		CreatedAt:   time.Now(),
	}

	if err := s.followRepo.Create(ctx, follow); err != nil {
		return nil, domain.NewInternalError("follow_failed", "Failed to create follow", err)
	}

	return follow, nil
}

// Unfollow removes a follow relationship
func (s *Service) Unfollow(ctx context.Context, followerID, followingID uuid.UUID) error {
	// Check currently following
	existing, _ := s.followRepo.GetByIDs(ctx, followerID, followingID)
	if existing == nil {
		return domain.ErrNotFollowing
	}

	return s.followRepo.Delete(ctx, followerID, followingID)
}

// ListFollowers retrieves the followers of an agent
func (s *Service) ListFollowers(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.AgentFollow, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}
	return s.followRepo.ListFollowers(ctx, agentID, limit, offset)
}

// ListFollowing retrieves the agents that an agent is following
func (s *Service) ListFollowing(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.AgentFollow, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}
	return s.followRepo.ListFollowing(ctx, agentID, limit, offset)
}

// IsFollowing checks if one agent is following another
func (s *Service) IsFollowing(ctx context.Context, followerID, followingID uuid.UUID) (bool, error) {
	return s.followRepo.IsFollowing(ctx, followerID, followingID)
}
