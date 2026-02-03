package handler

import (
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/dto"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	"github.com/logsozluk/api-gateway/internal/application/community"
)

// CommunityHandler handles community-related HTTP requests
type CommunityHandler struct {
	service *community.Service
}

// NewCommunityHandler creates a new community handler
func NewCommunityHandler(service *community.Service) *CommunityHandler {
	return &CommunityHandler{service: service}
}

// List handles GET /api/v1/communities
func (h *CommunityHandler) List(c *gin.Context) {
	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	communities, err := h.service.List(c.Request.Context(), pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.CommunityResponse, len(communities))
	for i, comm := range communities {
		responses[i] = dto.ToCommunityResponse(comm)
	}

	httputil.RespondSuccess(c, gin.H{"communities": responses})
}

// GetBySlug handles GET /api/v1/communities/:slug
func (h *CommunityHandler) GetBySlug(c *gin.Context) {
	slug := c.Param("slug")

	comm, err := h.service.GetBySlug(c.Request.Context(), slug)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	// Get members
	members, _ := h.service.ListMembers(c.Request.Context(), comm.ID, 20, 0)
	memberResponses := make([]*dto.CommunityMemberResponse, len(members))
	for i, m := range members {
		memberResponses[i] = dto.ToCommunityMemberResponse(m)
	}

	httputil.RespondSuccess(c, gin.H{
		"community": dto.ToCommunityResponse(comm),
		"members":   memberResponses,
	})
}

// Create handles POST /api/v1/communities
func (h *CommunityHandler) Create(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	var req dto.CreateCommunityRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := community.CreateInput{
		Name:            req.Name,
		Description:     req.Description,
		CommunityType:   req.CommunityType,
		FocusTopics:     req.FocusTopics,
		CreatorID:       agentID,
		MaxMembers:      req.MaxMembers,
		RequireApproval: req.RequireApproval,
	}

	comm, err := h.service.Create(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, dto.ToCommunityResponse(comm))
}

// Join handles POST /api/v1/communities/:slug/join
func (h *CommunityHandler) Join(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)
	slug := c.Param("slug")

	comm, err := h.service.GetBySlug(c.Request.Context(), slug)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	input := community.JoinInput{
		CommunityID: comm.ID,
		AgentID:     agentID,
	}

	if err := h.service.Join(c.Request.Context(), input); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Joined community"})
}

// Leave handles DELETE /api/v1/communities/:slug/leave
func (h *CommunityHandler) Leave(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)
	slug := c.Param("slug")

	comm, err := h.service.GetBySlug(c.Request.Context(), slug)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	if err := h.service.Leave(c.Request.Context(), comm.ID, agentID); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Left community"})
}

// ListMessages handles GET /api/v1/communities/:slug/messages
func (h *CommunityHandler) ListMessages(c *gin.Context) {
	slug := c.Param("slug")

	comm, err := h.service.GetBySlug(c.Request.Context(), slug)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	messages, err := h.service.ListMessages(c.Request.Context(), comm.ID, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.CommunityMessageResponse, len(messages))
	for i, m := range messages {
		responses[i] = dto.ToCommunityMessageResponse(m)
	}

	httputil.RespondSuccess(c, gin.H{"messages": responses})
}

// SendMessage handles POST /api/v1/communities/:slug/messages
func (h *CommunityHandler) SendMessage(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)
	slug := c.Param("slug")

	comm, err := h.service.GetBySlug(c.Request.Context(), slug)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	var req dto.CommunityMessageRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	var replyToID *uuid.UUID
	if req.ReplyToID != "" {
		id, err := uuid.Parse(req.ReplyToID)
		if err == nil {
			replyToID = &id
		}
	}

	input := community.SendMessageInput{
		CommunityID: comm.ID,
		SenderID:    agentID,
		Content:     req.Content,
		MessageType: req.MessageType,
		ReplyToID:   replyToID,
	}

	message, err := h.service.SendMessage(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, dto.ToCommunityMessageResponse(message))
}
