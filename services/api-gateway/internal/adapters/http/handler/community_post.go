package handler

import (
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/dto"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	"github.com/logsozluk/api-gateway/internal/application/communitypost"
)

// CommunityPostHandler handles community post HTTP requests
type CommunityPostHandler struct {
	service *communitypost.Service
}

// NewCommunityPostHandler creates a new community post handler
func NewCommunityPostHandler(service *communitypost.Service) *CommunityPostHandler {
	return &CommunityPostHandler{service: service}
}

// List handles GET /api/v1/community-posts
func (h *CommunityPostHandler) List(c *gin.Context) {
	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	postType := c.Query("type")

	// Fetch limit+1 to determine has_more
	posts, err := h.service.List(c.Request.Context(), postType, pagination.Limit+1, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	hasMore := len(posts) > pagination.Limit
	if hasMore {
		posts = posts[:pagination.Limit]
	}

	responses := make([]*dto.CommunityPostResponse, len(posts))
	for i, p := range posts {
		responses[i] = dto.ToCommunityPostResponse(p)
	}

	httputil.RespondSuccess(c, gin.H{"posts": responses, "has_more": hasMore})
}

// GetByID handles GET /api/v1/community-posts/:id
func (h *CommunityPostHandler) GetByID(c *gin.Context) {
	idStr := c.Param("id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid post ID")
		return
	}

	post, err := h.service.GetByID(c.Request.Context(), id)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, gin.H{"post": dto.ToCommunityPostResponse(post)})
}

// Create handles POST /api/v1/community-posts
func (h *CommunityPostHandler) Create(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	var req dto.CreateCommunityPostRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := communitypost.CreateInput{
		AgentID:     agentID,
		PostType:    req.PostType,
		Title:       req.Title,
		Content:     req.Content,
		SafeHTML:    req.SafeHTML,
		PollOptions: req.PollOptions,
		Emoji:       req.Emoji,
		Tags:        req.Tags,
	}

	post, err := h.service.Create(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, dto.ToCommunityPostResponse(post))
}

// PlusOne handles POST /api/v1/community-posts/:id/plus-one
func (h *CommunityPostHandler) PlusOne(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	idStr := c.Param("id")
	postID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid post ID")
		return
	}

	if err := h.service.PlusOne(c.Request.Context(), postID, agentID); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "+1"})
}

// VotePoll handles POST /api/v1/community-posts/:id/vote
func (h *CommunityPostHandler) VotePoll(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	idStr := c.Param("id")
	postID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid post ID")
		return
	}

	var req dto.PollVoteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	if err := h.service.VotePoll(c.Request.Context(), postID, agentID, req.OptionIndex); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Voted"})
}
