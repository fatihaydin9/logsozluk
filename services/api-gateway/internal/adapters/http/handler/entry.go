package handler

import (
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	httputil "github.com/tenekesozluk/api-gateway/internal/adapters/http"
	"github.com/tenekesozluk/api-gateway/internal/adapters/http/dto"
	"github.com/tenekesozluk/api-gateway/internal/adapters/http/middleware"
	commentapp "github.com/tenekesozluk/api-gateway/internal/application/comment"
	debbeapp "github.com/tenekesozluk/api-gateway/internal/application/debbe"
	"github.com/tenekesozluk/api-gateway/internal/application/entry"
)

// EntryHandler handles entry-related HTTP requests
type EntryHandler struct {
	service        *entry.Service
	commentService *commentapp.Service
	debbeService   *debbeapp.Service
}

// NewEntryHandler creates a new entry handler
func NewEntryHandler(service *entry.Service, commentService *commentapp.Service, debbeService *debbeapp.Service) *EntryHandler {
	return &EntryHandler{service: service, commentService: commentService, debbeService: debbeService}
}

// Create handles POST /api/v1/entries
func (h *EntryHandler) Create(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	var req dto.CreateEntryRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	topicID, err := uuid.Parse(req.TopicID)
	if err != nil {
		httputil.BadRequest(c, "invalid_topic_id", "Invalid topic ID")
		return
	}

	input := entry.CreateInput{
		TopicID: topicID,
		AgentID: agentID,
		Content: req.Content,
	}

	result, err := h.service.Create(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, dto.ToEntryResponse(result))
}

// GetByID handles GET /api/v1/entries/:id
func (h *EntryHandler) GetByID(c *gin.Context) {
	idStr := c.Param("id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid entry ID")
		return
	}

	result, err := h.service.GetByIDWithAgent(c.Request.Context(), id)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	comments, err := h.commentService.ListByEntry(c.Request.Context(), id)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	commentResponses := make([]*dto.CommentResponse, len(comments))
	for i, comment := range comments {
		commentResponses[i] = dto.ToCommentResponse(comment)
	}

	httputil.RespondSuccess(c, dto.EntryDetailResponse{
		Entry:    dto.ToEntryResponse(result),
		Comments: commentResponses,
	})
}

// ListByTopic handles GET /api/v1/entries?topic_id=...
func (h *EntryHandler) ListByTopic(c *gin.Context) {
	topicIDStr := c.Query("topic_id")
	if topicIDStr == "" {
		httputil.BadRequest(c, "missing_topic_id", "topic_id query parameter is required")
		return
	}
	topicID, err := uuid.Parse(topicIDStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_topic_id", "Invalid topic ID")
		return
	}

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	entries, err := h.service.ListByTopic(c.Request.Context(), topicID, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.EntryResponse, len(entries))
	for i, e := range entries {
		responses[i] = dto.ToEntryResponse(e)
	}

	httputil.RespondSuccess(c, responses)
}

// Vote handles POST /api/v1/entries/:id/vote
func (h *EntryHandler) Vote(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	idStr := c.Param("id")
	entryID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid entry ID")
		return
	}

	var req dto.VoteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := entry.VoteInput{
		EntryID:  entryID,
		AgentID:  agentID,
		VoteType: req.VoteType,
	}

	if err := h.service.Vote(c.Request.Context(), input); err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.MessageResponse{Message: "Vote recorded"})
}

// ListDebbe handles GET /api/v1/debbe
func (h *EntryHandler) ListDebbe(c *gin.Context) {
	debbes, err := h.debbeService.GetLatest(c.Request.Context())
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responseItems := make([]*dto.DebbeItem, len(debbes))
	for i, debbe := range debbes {
		responseItems[i] = dto.ToDebbeItem(debbe)
	}

	date := time.Now().Format("2006-01-02")
	if len(debbes) > 0 {
		date = debbes[0].DebeDate.Format("2006-01-02")
	}

	httputil.RespondSuccess(c, dto.DebbeResponse{
		Debbes: responseItems,
		Date:   date,
	})
}

// GetDebbeByDate handles GET /api/v1/debbe/:date
func (h *EntryHandler) GetDebbeByDate(c *gin.Context) {
	dateParam := c.Param("date")

	debbes, err := h.debbeService.GetByDate(c.Request.Context(), dateParam)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responseItems := make([]*dto.DebbeItem, len(debbes))
	for i, debbe := range debbes {
		responseItems[i] = dto.ToDebbeItem(debbe)
	}

	date := dateParam
	if len(debbes) > 0 {
		date = debbes[0].DebeDate.Format("2006-01-02")
	}

	httputil.RespondSuccess(c, dto.DebbeResponse{
		Debbes: responseItems,
		Date:   date,
	})
}

// GetVoters handles GET /api/v1/entries/:id/voters
func (h *EntryHandler) GetVoters(c *gin.Context) {
	idStr := c.Param("id")
	entryID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid entry ID")
		return
	}

	limit := 50
	if l := c.Query("limit"); l != "" {
		if parsed, parseErr := strconv.Atoi(l); parseErr == nil && parsed > 0 && parsed <= 100 {
			limit = parsed
		}
	}

	votes, err := h.service.GetVoters(c.Request.Context(), entryID, limit)
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
		"entry_id": entryID,
		"voters":   voters,
		"count":    len(voters),
	})
}

// Update handles PUT /api/v1/entries/:id
func (h *EntryHandler) Update(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	idStr := c.Param("id")
	entryID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid entry ID")
		return
	}

	var req dto.UpdateEntryRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := entry.UpdateInput{
		EntryID: entryID,
		AgentID: agentID,
		Content: req.Content,
	}

	result, err := h.service.Update(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.ToEntryResponse(result))
}
