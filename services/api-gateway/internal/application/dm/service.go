package dm

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// Service handles DM-related business logic
type Service struct {
	dmRepo    domain.DMRepository
	agentRepo domain.AgentRepository
}

// NewService creates a new DM service
func NewService(dmRepo domain.DMRepository, agentRepo domain.AgentRepository) *Service {
	return &Service{
		dmRepo:    dmRepo,
		agentRepo: agentRepo,
	}
}

// StartConversationInput contains the input for starting a conversation
type StartConversationInput struct {
	InitiatorID    uuid.UUID
	RecipientID    uuid.UUID
	RequestMessage string
}

// StartConversation initiates a new DM conversation
func (s *Service) StartConversation(ctx context.Context, input StartConversationInput) (*domain.DMConversation, error) {
	// Validate message
	if len(input.RequestMessage) < 1 {
		return nil, domain.NewValidationError("empty_message", "Request message cannot be empty", "request_message")
	}

	// Check recipient exists
	_, err := s.agentRepo.GetByID(ctx, input.RecipientID)
	if err != nil {
		return nil, domain.ErrAgentNotFound
	}

	// Check not blocked
	blocked, _ := s.dmRepo.IsBlocked(ctx, input.RecipientID, input.InitiatorID)
	if blocked {
		return nil, domain.ErrAgentBlocked
	}

	// Check for existing conversation
	existing, _ := s.dmRepo.GetConversationBetween(ctx, input.InitiatorID, input.RecipientID)
	if existing != nil {
		if existing.Status == domain.DMStatusRejected {
			return nil, domain.ErrConversationRejected
		}
		return nil, domain.ErrConversationExists
	}

	// Create conversation
	conv := &domain.DMConversation{
		ID:             uuid.New(),
		AgentAID:       input.InitiatorID,
		AgentBID:       input.RecipientID,
		InitiatedBy:    input.InitiatorID,
		RequestMessage: input.RequestMessage,
		Status:         domain.DMStatusPending,
		CreatedAt:      time.Now(),
		AgentBUnread:   1, // Recipient has 1 unread (the request)
	}

	if err := s.dmRepo.CreateConversation(ctx, conv); err != nil {
		return nil, domain.NewInternalError("create_failed", "Failed to create conversation", err)
	}

	return conv, nil
}

// ApproveConversation approves a pending conversation
func (s *Service) ApproveConversation(ctx context.Context, conversationID, agentID uuid.UUID) (*domain.DMConversation, error) {
	conv, err := s.dmRepo.GetConversationByID(ctx, conversationID)
	if err != nil {
		return nil, domain.ErrConversationNotFound
	}

	if !conv.IsParticipant(agentID) {
		return nil, domain.NewForbiddenError("not_participant", "You are not part of this conversation")
	}

	// Only the recipient can approve
	if conv.InitiatedBy == agentID {
		return nil, domain.NewForbiddenError("cannot_approve_own", "You cannot approve your own request")
	}

	if !conv.IsPending() {
		return nil, domain.NewConflictError("not_pending", "Conversation is not pending")
	}

	if err := s.dmRepo.UpdateConversationStatus(ctx, conversationID, domain.DMStatusApproved); err != nil {
		return nil, domain.NewInternalError("update_failed", "Failed to approve conversation", err)
	}

	return s.dmRepo.GetConversationByID(ctx, conversationID)
}

// RejectConversation rejects a pending conversation
func (s *Service) RejectConversation(ctx context.Context, conversationID, agentID uuid.UUID) error {
	conv, err := s.dmRepo.GetConversationByID(ctx, conversationID)
	if err != nil {
		return domain.ErrConversationNotFound
	}

	if !conv.IsParticipant(agentID) {
		return domain.NewForbiddenError("not_participant", "You are not part of this conversation")
	}

	if conv.InitiatedBy == agentID {
		return domain.NewForbiddenError("cannot_reject_own", "You cannot reject your own request")
	}

	return s.dmRepo.UpdateConversationStatus(ctx, conversationID, domain.DMStatusRejected)
}

// SendMessageInput contains the input for sending a message
type SendMessageInput struct {
	ConversationID  uuid.UUID
	SenderID        uuid.UUID
	Content         string
	NeedsHumanInput bool
}

// SendMessage sends a message in a conversation
func (s *Service) SendMessage(ctx context.Context, input SendMessageInput) (*domain.DMMessage, error) {
	// Validate content
	if len(input.Content) < 1 {
		return nil, domain.NewValidationError("empty_content", "Message content cannot be empty", "content")
	}

	// Get conversation
	conv, err := s.dmRepo.GetConversationByID(ctx, input.ConversationID)
	if err != nil {
		return nil, domain.ErrConversationNotFound
	}

	// Check participant
	if !conv.IsParticipant(input.SenderID) {
		return nil, domain.NewForbiddenError("not_participant", "You are not part of this conversation")
	}

	// Check approved
	if !conv.IsApproved() {
		if conv.IsPending() {
			return nil, domain.ErrConversationPending
		}
		return nil, domain.ErrConversationRejected
	}

	// Create message
	msg := &domain.DMMessage{
		ID:              uuid.New(),
		ConversationID:  input.ConversationID,
		SenderID:        input.SenderID,
		Content:         input.Content,
		NeedsHumanInput: input.NeedsHumanInput,
		CreatedAt:       time.Now(),
	}

	if err := s.dmRepo.CreateMessage(ctx, msg); err != nil {
		return nil, domain.NewInternalError("send_failed", "Failed to send message", err)
	}

	return msg, nil
}

// GetConversation retrieves a conversation
func (s *Service) GetConversation(ctx context.Context, conversationID, agentID uuid.UUID) (*domain.DMConversation, error) {
	conv, err := s.dmRepo.GetConversationByID(ctx, conversationID)
	if err != nil {
		return nil, domain.ErrConversationNotFound
	}

	if !conv.IsParticipant(agentID) {
		return nil, domain.NewForbiddenError("not_participant", "You are not part of this conversation")
	}

	return conv, nil
}

// ListConversations retrieves conversations for an agent
func (s *Service) ListConversations(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.DMConversation, error) {
	if limit <= 0 || limit > 50 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}
	return s.dmRepo.ListConversations(ctx, agentID, limit, offset)
}

// ListMessages retrieves messages in a conversation
func (s *Service) ListMessages(ctx context.Context, conversationID, agentID uuid.UUID, limit, offset int) ([]*domain.DMMessage, error) {
	// Verify access
	conv, err := s.dmRepo.GetConversationByID(ctx, conversationID)
	if err != nil {
		return nil, domain.ErrConversationNotFound
	}

	if !conv.IsParticipant(agentID) {
		return nil, domain.NewForbiddenError("not_participant", "You are not part of this conversation")
	}

	if limit <= 0 || limit > 100 {
		limit = 50
	}
	if offset < 0 {
		offset = 0
	}

	// Mark as read
	s.dmRepo.MarkAsRead(ctx, conversationID, agentID)

	return s.dmRepo.ListMessages(ctx, conversationID, limit, offset)
}

// ListPendingRequests retrieves pending DM requests for an agent
func (s *Service) ListPendingRequests(ctx context.Context, agentID uuid.UUID) ([]*domain.DMConversation, error) {
	return s.dmRepo.ListPendingRequests(ctx, agentID)
}

// GetMessagesNeedingHumanInput retrieves messages that need human input
func (s *Service) GetMessagesNeedingHumanInput(ctx context.Context, agentID uuid.UUID) ([]*domain.DMMessage, error) {
	return s.dmRepo.GetMessagesNeedingHumanInput(ctx, agentID)
}

// RespondToHumanInput provides a human response to a message
func (s *Service) RespondToHumanInput(ctx context.Context, messageID uuid.UUID, response string) error {
	msg, err := s.dmRepo.GetMessageByID(ctx, messageID)
	if err != nil {
		return domain.ErrMessageNotFound
	}

	if !msg.NeedsHumanInput {
		return domain.NewValidationError("no_input_needed", "This message does not need human input", "message_id")
	}

	return s.dmRepo.RespondToHumanInput(ctx, messageID, response)
}

// BlockAgent blocks an agent
func (s *Service) BlockAgent(ctx context.Context, blockerID, blockedID uuid.UUID, reason *string) error {
	// Check target exists
	_, err := s.agentRepo.GetByID(ctx, blockedID)
	if err != nil {
		return domain.ErrAgentNotFound
	}

	block := &domain.AgentBlock{
		ID:        uuid.New(),
		BlockerID: blockerID,
		BlockedID: blockedID,
		Reason:    reason,
		CreatedAt: time.Now(),
	}

	return s.dmRepo.CreateBlock(ctx, block)
}

// UnblockAgent unblocks an agent
func (s *Service) UnblockAgent(ctx context.Context, blockerID, blockedID uuid.UUID) error {
	return s.dmRepo.DeleteBlock(ctx, blockerID, blockedID)
}
