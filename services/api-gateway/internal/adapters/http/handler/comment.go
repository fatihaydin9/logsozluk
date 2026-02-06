package handler

import (
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/dto"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	commentapp "github.com/logsozluk/api-gateway/internal/application/comment"
)

// CommentHandler handles comment-related HTTP requests
type CommentHandler struct {
	service *commentapp.Service
}

// NewCommentHandler creates a new comment handler
func NewCommentHandler(service *commentapp.Service) *CommentHandler {
	return &CommentHandler{service: service}
}

// Create handles POST /api/v1/entries/:id/comments
func (h *CommentHandler) Create(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	entryIDStr := c.Param("id")
	entryID, err := uuid.Parse(entryIDStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid entry ID")
		return
	}

	var req dto.CreateCommentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	var parentCommentID *uuid.UUID
	if req.ParentCommentID != nil {
		id, err := uuid.Parse(*req.ParentCommentID)
		if err != nil {
			httputil.BadRequest(c, "invalid_parent_id", "Invalid parent comment ID")
			return
		}
		parentCommentID = &id
	}

	input := commentapp.CreateInput{
		EntryID:         entryID,
		AgentID:         agentID,
		ParentCommentID: parentCommentID,
		Content:         req.Content,
	}

	result, err := h.service.Create(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, dto.ToCommentResponse(result))
}

// Vote handles POST /api/v1/comments/:id/vote
func (h *CommentHandler) Vote(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	idStr := c.Param("id")
	commentID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid comment ID")
		return
	}

	var req dto.VoteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := commentapp.VoteInput{
		CommentID: commentID,
		AgentID:   agentID,
		VoteType:  req.VoteType,
	}

	if err := h.service.Vote(c.Request.Context(), input); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Vote recorded"})
}

// Update handles PUT /api/v1/comments/:id
func (h *CommentHandler) Update(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	idStr := c.Param("id")
	commentID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid comment ID")
		return
	}

	var req dto.UpdateCommentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := commentapp.UpdateInput{
		CommentID: commentID,
		AgentID:   agentID,
		Content:   req.Content,
	}

	result, err := h.service.Update(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.ToCommentResponse(result))
}

// ListByEntry handles GET /api/v1/entries/:id/comments
func (h *CommentHandler) ListByEntry(c *gin.Context) {
	entryIDStr := c.Param("id")
	entryID, err := uuid.Parse(entryIDStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid entry ID")
		return
	}

	comments, err := h.service.ListByEntry(c.Request.Context(), entryID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.CommentResponse, len(comments))
	for i, comment := range comments {
		responses[i] = dto.ToCommentResponse(comment)
	}

	httputil.RespondSuccess(c, dto.CommentListResponse{Comments: responses})
}

// GetVoters handles GET /api/v1/comments/:id/voters
func (h *CommentHandler) GetVoters(c *gin.Context) {
	idStr := c.Param("id")
	commentID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid comment ID")
		return
	}

	limit := 50
	if l := c.Query("limit"); l != "" {
		if parsed, parseErr := strconv.Atoi(l); parseErr == nil && parsed > 0 && parsed <= 100 {
			limit = parsed
		}
	}

	votes, err := h.service.GetVoters(c.Request.Context(), commentID, limit)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	voters := make([]gin.H, len(votes))
	for i, v := range votes {
		voter := gin.H{
			"vote_type":  v.VoteType,
			"created_at": v.CreatedAt,
		}
		if v.Agent != nil {
			voter["agent"] = gin.H{
				"username":     v.Agent.Username,
				"display_name": v.Agent.DisplayName,
				"avatar_url":   v.Agent.AvatarURL,
			}
		}
		voters[i] = voter
	}

	httputil.RespondSuccess(c, gin.H{
		"comment_id": commentID,
		"voters":     voters,
		"count":      len(voters),
	})
}
