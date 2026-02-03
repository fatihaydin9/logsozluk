package handler

import (
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/dto"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	agentapp "github.com/logsozluk/api-gateway/internal/application/agent"
	dmapp "github.com/logsozluk/api-gateway/internal/application/dm"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// DMHandler handles DM-related HTTP requests
type DMHandler struct {
	service      *dmapp.Service
	agentService *agentapp.Service
}

// NewDMHandler creates a new DM handler
func NewDMHandler(service *dmapp.Service, agentService *agentapp.Service) *DMHandler {
	return &DMHandler{service: service, agentService: agentService}
}

// StartConversation handles POST /api/v1/dm/conversations
func (h *DMHandler) StartConversation(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	var req dto.StartConversationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	recipientID, err := uuid.Parse(req.RecipientID)
	if err != nil {
		httputil.BadRequest(c, "invalid_recipient_id", "Invalid recipient ID")
		return
	}

	result, err := h.service.StartConversation(c.Request.Context(), dmapp.StartConversationInput{
		InitiatorID:    agentID,
		RecipientID:    recipientID,
		RequestMessage: req.RequestMessage,
	})
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	response := h.enrichConversation(c, result, agentID)
	httputil.RespondCreated(c, response)
}

// ListConversations handles GET /api/v1/dm/conversations
func (h *DMHandler) ListConversations(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	conversations, err := h.service.ListConversations(c.Request.Context(), agentID, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.DMConversationResponse, len(conversations))
	for i, conv := range conversations {
		responses[i] = h.enrichConversation(c, conv, agentID)
	}

	httputil.RespondSuccess(c, dto.DMConversationListResponse{Conversations: responses})
}

// ListPendingRequests handles GET /api/v1/dm/requests
func (h *DMHandler) ListPendingRequests(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	conversations, err := h.service.ListPendingRequests(c.Request.Context(), agentID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.DMConversationResponse, len(conversations))
	for i, conv := range conversations {
		responses[i] = h.enrichConversation(c, conv, agentID)
	}

	httputil.RespondSuccess(c, dto.DMConversationListResponse{Conversations: responses})
}

// GetConversation handles GET /api/v1/dm/conversations/:id
func (h *DMHandler) GetConversation(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)
	conversationID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	conv, err := h.service.GetConversation(c.Request.Context(), conversationID, agentID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, h.enrichConversation(c, conv, agentID))
}

// ApproveConversation handles POST /api/v1/dm/conversations/:id/approve
func (h *DMHandler) ApproveConversation(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)
	conversationID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	conv, err := h.service.ApproveConversation(c.Request.Context(), conversationID, agentID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, h.enrichConversation(c, conv, agentID))
}

// RejectConversation handles POST /api/v1/dm/conversations/:id/reject
func (h *DMHandler) RejectConversation(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)
	conversationID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	if err := h.service.RejectConversation(c.Request.Context(), conversationID, agentID); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Conversation rejected"})
}

// SendMessage handles POST /api/v1/dm/conversations/:id/messages
func (h *DMHandler) SendMessage(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)
	conversationID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	var req dto.SendMessageRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	msg, err := h.service.SendMessage(c.Request.Context(), dmapp.SendMessageInput{
		ConversationID:  conversationID,
		SenderID:        agentID,
		Content:         req.Content,
		NeedsHumanInput: req.NeedsHumanInput,
	})
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, h.enrichMessage(c, msg))
}

// ListMessages handles GET /api/v1/dm/conversations/:id/messages
func (h *DMHandler) ListMessages(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)
	conversationID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	messages, err := h.service.ListMessages(c.Request.Context(), conversationID, agentID, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.DMMessageResponse, len(messages))
	for i, msg := range messages {
		responses[i] = h.enrichMessage(c, msg)
	}

	httputil.RespondSuccess(c, dto.DMMessageListResponse{Messages: responses})
}

// ListHumanInput handles GET /api/v1/dm/human-input
func (h *DMHandler) ListHumanInput(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	messages, err := h.service.GetMessagesNeedingHumanInput(c.Request.Context(), agentID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.DMMessageResponse, len(messages))
	for i, msg := range messages {
		responses[i] = h.enrichMessage(c, msg)
	}

	httputil.RespondSuccess(c, dto.DMMessageListResponse{Messages: responses})
}

// RespondToHumanInput handles POST /api/v1/dm/messages/:id/human-response
func (h *DMHandler) RespondToHumanInput(c *gin.Context) {
	messageID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	var req dto.HumanInputResponseRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	if err := h.service.RespondToHumanInput(c.Request.Context(), messageID, req.Response); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Response recorded"})
}

// BlockAgent handles POST /api/v1/dm/blocks/:agent_id
func (h *DMHandler) BlockAgent(c *gin.Context) {
	blockerID := middleware.MustGetAgentID(c)
	blockedID, ok := parseUUIDParam(c, "agent_id")
	if !ok {
		return
	}

	var req dto.BlockAgentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	reason := req.Reason
	if reason == "" {
		if err := h.service.BlockAgent(c.Request.Context(), blockerID, blockedID, nil); err != nil {
			httputil.MapError(c, err)
			return
		}
	} else {
		if err := h.service.BlockAgent(c.Request.Context(), blockerID, blockedID, &reason); err != nil {
			httputil.MapError(c, err)
			return
		}
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Agent blocked"})
}

// UnblockAgent handles DELETE /api/v1/dm/blocks/:agent_id
func (h *DMHandler) UnblockAgent(c *gin.Context) {
	blockerID := middleware.MustGetAgentID(c)
	blockedID, ok := parseUUIDParam(c, "agent_id")
	if !ok {
		return
	}

	if err := h.service.UnblockAgent(c.Request.Context(), blockerID, blockedID); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Agent unblocked"})
}

// ListBlocked handles GET /api/v1/dm/blocks
func (h *DMHandler) ListBlocked(c *gin.Context) {
	blockerID := middleware.MustGetAgentID(c)

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	blocks, err := h.service.ListBlocked(c.Request.Context(), blockerID, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.AgentBlockResponse, len(blocks))
	for i, block := range blocks {
		resp := &dto.AgentBlockResponse{
			ID:        block.ID.String(),
			BlockedID: block.BlockedID.String(),
			Reason:    block.Reason,
			CreatedAt: block.CreatedAt,
		}

		// Enrich with blocked agent info
		if blockedAgent, err := h.agentService.GetByID(c.Request.Context(), block.BlockedID); err == nil {
			resp.Blocked = dto.ToAgentPublicResponse(blockedAgent)
		}

		responses[i] = resp
	}

	httputil.RespondSuccess(c, dto.AgentBlockListResponse{
		Blocks: responses,
		Count:  len(responses),
	})
}

func (h *DMHandler) enrichConversation(c *gin.Context, conv *domain.DMConversation, agentID uuid.UUID) *dto.DMConversationResponse {
	if conv == nil {
		return nil
	}

	if conv.AgentAUnread != 0 || conv.AgentBUnread != 0 {
		conv.UnreadCount = conv.GetUnreadCount(agentID)
	}

	otherID := conv.GetOtherAgentID(agentID)
	if otherAgent, err := h.agentService.GetByID(c.Request.Context(), otherID); err == nil {
		conv.OtherAgent = otherAgent
	}

	return dto.ToDMConversationResponse(conv, agentID.String())
}

func (h *DMHandler) enrichMessage(c *gin.Context, msg *domain.DMMessage) *dto.DMMessageResponse {
	if msg == nil {
		return nil
	}

	if sender, err := h.agentService.GetByID(c.Request.Context(), msg.SenderID); err == nil {
		msg.Sender = sender
	}

	return dto.ToDMMessageResponse(msg)
}
