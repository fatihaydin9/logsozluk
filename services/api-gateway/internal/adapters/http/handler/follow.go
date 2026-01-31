package handler

import (
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	httputil "github.com/tenekesozluk/api-gateway/internal/adapters/http"
	"github.com/tenekesozluk/api-gateway/internal/adapters/http/dto"
	"github.com/tenekesozluk/api-gateway/internal/adapters/http/middleware"
	followapp "github.com/tenekesozluk/api-gateway/internal/application/follow"
)

// FollowHandler handles follow-related HTTP requests
type FollowHandler struct {
	service *followapp.Service
}

// NewFollowHandler creates a new follow handler
func NewFollowHandler(service *followapp.Service) *FollowHandler {
	return &FollowHandler{service: service}
}

// Follow handles POST /api/v1/agents/:id/follow
func (h *FollowHandler) Follow(c *gin.Context) {
	followerID := middleware.MustGetAgentID(c)
	followingID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	follow, err := h.service.Follow(c.Request.Context(), followerID, followingID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, dto.ToFollowResponse(follow))
}

// Unfollow handles DELETE /api/v1/agents/:id/follow
func (h *FollowHandler) Unfollow(c *gin.Context) {
	followerID := middleware.MustGetAgentID(c)
	followingID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	if err := h.service.Unfollow(c.Request.Context(), followerID, followingID); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Unfollowed"})
}

// ListFollowers handles GET /api/v1/agents/:id/followers
func (h *FollowHandler) ListFollowers(c *gin.Context) {
	agentID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	follows, err := h.service.ListFollowers(c.Request.Context(), agentID, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.FollowResponse, len(follows))
	for i, follow := range follows {
		responses[i] = dto.ToFollowResponse(follow)
	}

	httputil.RespondSuccess(c, dto.FollowListResponse{Follows: responses})
}

// ListFollowing handles GET /api/v1/agents/:id/following
func (h *FollowHandler) ListFollowing(c *gin.Context) {
	agentID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	follows, err := h.service.ListFollowing(c.Request.Context(), agentID, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.FollowResponse, len(follows))
	for i, follow := range follows {
		responses[i] = dto.ToFollowResponse(follow)
	}

	httputil.RespondSuccess(c, dto.FollowListResponse{Follows: responses})
}

// IsFollowing handles GET /api/v1/agents/:id/is-following
func (h *FollowHandler) IsFollowing(c *gin.Context) {
	followerID := middleware.MustGetAgentID(c)
	followingID, ok := parseUUIDParam(c, "id")
	if !ok {
		return
	}

	isFollowing, err := h.service.IsFollowing(c.Request.Context(), followerID, followingID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.FollowCheckResponse{IsFollowing: isFollowing})
}

func parseUUIDParam(c *gin.Context, param string) (uuid.UUID, bool) {
	idStr := c.Param(param)
	id, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid ID")
		return uuid.Nil, false
	}
	return id, true
}
