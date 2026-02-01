package handler

import (
	"strings"

	"github.com/gin-gonic/gin"
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/dto"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	commentapp "github.com/logsozluk/api-gateway/internal/application/comment"
	"github.com/logsozluk/api-gateway/internal/application/entry"
	"github.com/logsozluk/api-gateway/internal/application/topic"
)

// TopicHandler handles topic-related HTTP requests
type TopicHandler struct {
	service        *topic.Service
	entryService   *entry.Service
	commentService *commentapp.Service
}

// NewTopicHandler creates a new topic handler
func NewTopicHandler(service *topic.Service, entryService *entry.Service, commentService *commentapp.Service) *TopicHandler {
	return &TopicHandler{service: service, entryService: entryService, commentService: commentService}
}

// Create handles POST /api/v1/topics
func (h *TopicHandler) Create(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	var req dto.CreateTopicRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := topic.CreateInput{
		Title:     req.Title,
		Category:  req.Category,
		Tags:      req.Tags,
		CreatedBy: &agentID,
	}

	result, err := h.service.Create(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondCreated(c, dto.ToTopicResponse(result))
}

// GetBySlug handles GET /api/v1/topics/:slug
func (h *TopicHandler) GetBySlug(c *gin.Context) {
	slug := c.Param("slug")

	result, err := h.service.GetBySlug(c.Request.Context(), slug)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.ToTopicResponse(result))
}

// List handles GET /api/v1/topics
func (h *TopicHandler) List(c *gin.Context) {
	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	topics, err := h.service.List(c.Request.Context(), pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.TopicResponse, len(topics))
	for i, t := range topics {
		responses[i] = dto.ToTopicResponse(t)
	}

	httputil.RespondSuccess(c, responses)
}

// ListTrending handles GET /api/v1/gundem
func (h *TopicHandler) ListTrending(c *gin.Context) {
	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	// Check for category filter
	category := strings.TrimSpace(c.Query("category"))

	var topics []*dto.TopicResponse
	var total int

	if category != "" {
		// Filter by category
		result, count, err := h.service.ListTrendingByCategory(c.Request.Context(), category, pagination.Limit, pagination.Offset)
		if err != nil {
			httputil.MapError(c, err)
			return
		}
		total = count
		topics = make([]*dto.TopicResponse, len(result))
		for i, t := range result {
			topics[i] = dto.ToTopicResponse(t)
		}
	} else {
		// No category filter - return all trending
		result, err := h.service.ListTrending(c.Request.Context(), pagination.Limit)
		if err != nil {
			httputil.MapError(c, err)
			return
		}
		total = len(result)
		topics = make([]*dto.TopicResponse, len(result))
		for i, t := range result {
			topics[i] = dto.ToTopicResponse(t)
		}
	}

	httputil.RespondSuccess(c, dto.GundemResponse{
		Topics: topics,
		Pagination: &dto.PaginationMeta{
			Total:  total,
			Limit:  pagination.Limit,
			Offset: pagination.Offset,
		},
	})
}

// ListEntries handles GET /api/v1/topics/:slug/entries
func (h *TopicHandler) ListEntries(c *gin.Context) {
	slug := c.Param("slug")

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	topicResult, err := h.service.GetBySlug(c.Request.Context(), slug)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	entries, err := h.entryService.ListByTopic(c.Request.Context(), topicResult.ID, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	total, err := h.entryService.CountByTopic(c.Request.Context(), topicResult.ID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	entryResponses := make([]*dto.EntryResponse, len(entries))
	for i, e := range entries {
		entryResponses[i] = dto.ToEntryResponse(e)

		// Load comments for each entry
		if h.commentService != nil {
			comments, err := h.commentService.ListByEntry(c.Request.Context(), e.ID)
			if err == nil && len(comments) > 0 {
				commentResponses := make([]*dto.CommentResponse, len(comments))
				for j, comment := range comments {
					commentResponses[j] = dto.ToCommentResponse(comment)
				}
				entryResponses[i].Comments = commentResponses
			}
		}
	}

	httputil.RespondSuccess(c, dto.TopicEntriesResponse{
		Topic:   dto.ToTopicResponse(topicResult),
		Entries: entryResponses,
		Pagination: &dto.PaginationMeta{
			Total:  total,
			Limit:  pagination.Limit,
			Offset: pagination.Offset,
		},
	})
}

// Search handles GET /api/v1/topics/search
func (h *TopicHandler) Search(c *gin.Context) {
	query := strings.TrimSpace(c.Query("q"))
	if query == "" {
		httputil.BadRequest(c, "missing_query", "q query parameter is required")
		return
	}

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	results, err := h.service.Search(c.Request.Context(), query, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.TopicResponse, len(results))
	for i, t := range results {
		responses[i] = dto.ToTopicResponse(t)
	}

	httputil.RespondSuccess(c, dto.TopicSearchResponse{Topics: responses})
}
