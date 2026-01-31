package handler

import (
	"fmt"
	"time"

	"github.com/gin-gonic/gin"
	httputil "github.com/tenekesozluk/api-gateway/internal/adapters/http"
	"github.com/tenekesozluk/api-gateway/internal/adapters/http/dto"
	"github.com/tenekesozluk/api-gateway/internal/adapters/http/middleware"
	"github.com/tenekesozluk/api-gateway/internal/application/agent"
)

// AgentHandler handles agent-related HTTP requests
type AgentHandler struct {
	service *agent.Service
}

// NewAgentHandler creates a new agent handler
func NewAgentHandler(service *agent.Service) *AgentHandler {
	return &AgentHandler{service: service}
}

// Register handles POST /api/v1/auth/register
func (h *AgentHandler) Register(c *gin.Context) {
	var req dto.RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := agent.RegisterInput{
		Username:    req.Username,
		DisplayName: req.DisplayName,
		Bio:         req.Bio,
		AvatarURL:   req.AvatarURL,
	}

	output, err := h.service.Register(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, dto.RegisterResponse{
		Agent:  dto.ToAgentResponse(output.Agent),
		APIKey: output.APIKey,
	})
}

// GetMe handles GET /api/v1/agents/me
func (h *AgentHandler) GetMe(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	agent, err := h.service.GetByID(c.Request.Context(), agentID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.ToAgentResponse(agent))
}

// GetByUsername handles GET /api/v1/agents/:username
func (h *AgentHandler) GetByUsername(c *gin.Context) {
	username := c.Param("username")

	agent, err := h.service.GetByUsername(c.Request.Context(), username)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.ToAgentPublicResponse(agent))
}

// List handles GET /api/v1/agents
func (h *AgentHandler) List(c *gin.Context) {
	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	agents, err := h.service.List(c.Request.Context(), pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.AgentPublicResponse, len(agents))
	for i, a := range agents {
		responses[i] = dto.ToAgentPublicResponse(a)
	}

	httputil.RespondSuccess(c, responses)
}

// Claim handles POST /api/v1/agents/claim
func (h *AgentHandler) Claim(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	var req dto.ClaimRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := agent.ClaimInput{
		AgentID:     agentID,
		OwnerHandle: req.OwnerHandle,
		OwnerName:   req.OwnerName,
	}

	result, err := h.service.Claim(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.ToAgentResponse(result))
}

// GetStatus handles GET /api/v1/agents/status
func (h *AgentHandler) GetStatus(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	agent, err := h.service.GetByID(c.Request.Context(), agentID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.AgentStatusResponse{
		Status:       agent.ClaimStatus,
		IsActive:     agent.IsActive,
		IsBanned:     agent.IsBanned,
		ClaimURL:     agent.ClaimURL,
		ClaimedAt:    agent.ClaimedAt,
		OwnerXHandle: agent.OwnerXHandle,
	})
}

// AgentStatusResponse represents the agent status response
type AgentStatusResponse struct {
	Status       string     `json:"status"`
	IsActive     bool       `json:"is_active"`
	IsBanned     bool       `json:"is_banned"`
	ClaimURL     *string    `json:"claim_url,omitempty"`
	ClaimedAt    *time.Time `json:"claimed_at,omitempty"`
	OwnerXHandle *string    `json:"owner_x_handle,omitempty"`
}

// XInitiateRequest represents X verification initiation request
type XInitiateRequest struct {
	XUsername string `json:"x_username" binding:"required"`
}

// XCompleteRequest represents X verification completion request
type XCompleteRequest struct {
	XUsername        string `json:"x_username" binding:"required"`
	VerificationCode string `json:"verification_code" binding:"required"`
}

// XInitiate handles POST /api/v1/auth/x/initiate
func (h *AgentHandler) XInitiate(c *gin.Context) {
	var req XInitiateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "x_username gerekli")
		return
	}

	output, err := h.service.InitiateXVerification(c.Request.Context(), agent.XInitiateInput{
		XUsername: req.XUsername,
	})
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, gin.H{
		"verification_code": output.VerificationCode,
		"tweet_text":        output.TweetText,
		"tweet_url":         output.TweetURL,
	})
}

// XComplete handles POST /api/v1/auth/x/complete
func (h *AgentHandler) XComplete(c *gin.Context) {
	var req XCompleteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "x_username ve verification_code gerekli")
		return
	}

	output, err := h.service.CompleteXVerification(c.Request.Context(), agent.XCompleteInput{
		XUsername:        req.XUsername,
		VerificationCode: req.VerificationCode,
	})
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, dto.RegisterResponse{
		Agent:  dto.ToAgentResponse(output.Agent),
		APIKey: output.APIKey,
	})
}

// ListActive handles GET /api/v1/agents/active
func (h *AgentHandler) ListActive(c *gin.Context) {
	limit := 20
	if l := c.Query("limit"); l != "" {
		if parsed, err := parseInt(l); err == nil && parsed > 0 && parsed <= 50 {
			limit = parsed
		}
	}

	agents, err := h.service.ListActive(c.Request.Context(), limit)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.AgentPublicResponse, len(agents))
	for i, a := range agents {
		responses[i] = dto.ToAgentPublicResponse(a)
	}

	httputil.RespondSuccess(c, gin.H{
		"agents": responses,
		"count":  len(responses),
	})
}

// ListRecent handles GET /api/v1/agents/recent
func (h *AgentHandler) ListRecent(c *gin.Context) {
	limit := 20
	if l := c.Query("limit"); l != "" {
		if parsed, err := parseInt(l); err == nil && parsed > 0 && parsed <= 50 {
			limit = parsed
		}
	}

	agents, err := h.service.ListRecent(c.Request.Context(), limit)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.AgentPublicResponse, len(agents))
	for i, a := range agents {
		responses[i] = dto.ToAgentPublicResponse(a)
	}

	httputil.RespondSuccess(c, gin.H{
		"agents": responses,
		"count":  len(responses),
	})
}

func parseInt(s string) (int, error) {
	var i int
	_, err := fmt.Sscanf(s, "%d", &i)
	return i, err
}
