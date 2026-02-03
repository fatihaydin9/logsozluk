package community

import (
	"context"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// Service handles community business logic
type Service struct {
	repo domain.CommunityRepository
}

// NewService creates a new community service
func NewService(repo domain.CommunityRepository) *Service {
	return &Service{repo: repo}
}

// CreateInput contains the input for creating a community
type CreateInput struct {
	Name            string
	Description     string
	CommunityType   string
	FocusTopics     []string
	CreatorID       uuid.UUID
	MaxMembers      int
	RequireApproval bool
}

// Create creates a new community
func (s *Service) Create(ctx context.Context, input CreateInput) (*domain.Community, error) {
	// Generate slug
	slug := generateSlug(input.Name)

	// Validate community type
	communityType := domain.CommunityType(input.CommunityType)
	if communityType == "" {
		communityType = domain.CommunityTypeOpen
	}

	maxMembers := input.MaxMembers
	if maxMembers <= 0 {
		maxMembers = 50
	}

	community := &domain.Community{
		ID:              uuid.New(),
		Name:            input.Name,
		Slug:            slug,
		Description:     &input.Description,
		CommunityType:   communityType,
		FocusTopics:     input.FocusTopics,
		CreatedBy:       input.CreatorID,
		MaxMembers:      maxMembers,
		RequireApproval: input.RequireApproval,
		IsActive:        true,
	}

	if err := s.repo.Create(ctx, community); err != nil {
		return nil, fmt.Errorf("failed to create community: %w", err)
	}

	// Add creator as owner
	member := &domain.CommunityMember{
		CommunityID: community.ID,
		AgentID:     input.CreatorID,
		Role:        domain.MemberRoleOwner,
		Status:      domain.MemberStatusActive,
	}
	if err := s.repo.AddMember(ctx, member); err != nil {
		return nil, fmt.Errorf("failed to add creator as member: %w", err)
	}

	return community, nil
}

// GetByID retrieves a community by ID
func (s *Service) GetByID(ctx context.Context, id uuid.UUID) (*domain.Community, error) {
	return s.repo.GetByID(ctx, id)
}

// GetBySlug retrieves a community by slug
func (s *Service) GetBySlug(ctx context.Context, slug string) (*domain.Community, error) {
	return s.repo.GetBySlug(ctx, slug)
}

// List lists all communities
func (s *Service) List(ctx context.Context, limit, offset int) ([]*domain.Community, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	return s.repo.List(ctx, limit, offset)
}

// ListByAgent lists communities an agent is a member of
func (s *Service) ListByAgent(ctx context.Context, agentID uuid.UUID) ([]*domain.Community, error) {
	return s.repo.ListByAgent(ctx, agentID)
}

// JoinInput contains the input for joining a community
type JoinInput struct {
	CommunityID uuid.UUID
	AgentID     uuid.UUID
}

// Join adds an agent to a community
func (s *Service) Join(ctx context.Context, input JoinInput) error {
	community, err := s.repo.GetByID(ctx, input.CommunityID)
	if err != nil {
		return fmt.Errorf("community not found: %w", err)
	}

	// Check if already a member
	existing, _ := s.repo.GetMember(ctx, input.CommunityID, input.AgentID)
	if existing != nil && existing.Status == domain.MemberStatusActive {
		return domain.ErrAlreadyFollowing // reuse for "already member"
	}

	// Check member limit
	if community.MemberCount >= community.MaxMembers {
		return domain.NewValidationError("member_limit", "Community has reached maximum members", "community_id")
	}

	status := domain.MemberStatusActive
	if community.RequireApproval {
		status = domain.MemberStatusPending
	}

	member := &domain.CommunityMember{
		CommunityID: input.CommunityID,
		AgentID:     input.AgentID,
		Role:        domain.MemberRoleMember,
		Status:      status,
	}

	return s.repo.AddMember(ctx, member)
}

// Leave removes an agent from a community
func (s *Service) Leave(ctx context.Context, communityID, agentID uuid.UUID) error {
	return s.repo.RemoveMember(ctx, communityID, agentID)
}

// ListMembers lists members of a community
func (s *Service) ListMembers(ctx context.Context, communityID uuid.UUID, limit, offset int) ([]*domain.CommunityMember, error) {
	if limit <= 0 || limit > 100 {
		limit = 50
	}
	return s.repo.ListMembers(ctx, communityID, limit, offset)
}

// SendMessageInput contains the input for sending a message
type SendMessageInput struct {
	CommunityID uuid.UUID
	SenderID    uuid.UUID
	Content     string
	MessageType string
	ReplyToID   *uuid.UUID
}

// SendMessage sends a message to a community
func (s *Service) SendMessage(ctx context.Context, input SendMessageInput) (*domain.CommunityMessage, error) {
	// Verify sender is a member
	member, err := s.repo.GetMember(ctx, input.CommunityID, input.SenderID)
	if err != nil || member.Status != domain.MemberStatusActive {
		return nil, domain.NewForbiddenError("not_member", "You must be an active member to send messages")
	}

	messageType := input.MessageType
	if messageType == "" {
		messageType = "text"
	}

	message := &domain.CommunityMessage{
		ID:          uuid.New(),
		CommunityID: input.CommunityID,
		SenderID:    input.SenderID,
		Content:     input.Content,
		MessageType: messageType,
		ReplyToID:   input.ReplyToID,
	}

	if err := s.repo.CreateMessage(ctx, message); err != nil {
		return nil, fmt.Errorf("failed to create message: %w", err)
	}

	return message, nil
}

// ListMessages lists messages in a community
func (s *Service) ListMessages(ctx context.Context, communityID uuid.UUID, limit, offset int) ([]*domain.CommunityMessage, error) {
	if limit <= 0 || limit > 100 {
		limit = 50
	}
	return s.repo.ListMessages(ctx, communityID, limit, offset)
}

// Helper function to generate slug
func generateSlug(name string) string {
	slug := strings.ToLower(name)
	slug = strings.ReplaceAll(slug, " ", "-")
	slug = strings.ReplaceAll(slug, "ş", "s")
	slug = strings.ReplaceAll(slug, "ğ", "g")
	slug = strings.ReplaceAll(slug, "ü", "u")
	slug = strings.ReplaceAll(slug, "ö", "o")
	slug = strings.ReplaceAll(slug, "ı", "i")
	slug = strings.ReplaceAll(slug, "ç", "c")
	return slug
}
