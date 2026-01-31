package handler

import (
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/adapters/http/dto"
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	"github.com/logsozluk/api-gateway/internal/application/task"
)

// TaskHandler handles task-related HTTP requests
type TaskHandler struct {
	service *task.Service
}

// NewTaskHandler creates a new task handler
func NewTaskHandler(service *task.Service) *TaskHandler {
	return &TaskHandler{service: service}
}

// ListPending handles GET /api/v1/tasks
func (h *TaskHandler) ListPending(c *gin.Context) {
	limit := 10
	if l := c.Query("limit"); l != "" {
		if parsed, err := strconv.Atoi(l); err == nil && parsed > 0 && parsed <= 50 {
			limit = parsed
		}
	}

	tasks, err := h.service.ListPending(c.Request.Context(), limit)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.TaskResponse, len(tasks))
	for i, t := range tasks {
		responses[i] = dto.ToTaskResponse(t)
	}

	httputil.RespondSuccess(c, responses)
}

// GetByID handles GET /api/v1/tasks/:id
func (h *TaskHandler) GetByID(c *gin.Context) {
	idStr := c.Param("id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid task ID")
		return
	}

	result, err := h.service.GetByID(c.Request.Context(), id)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.ToTaskResponse(result))
}

// Claim handles POST /api/v1/tasks/:id/claim
func (h *TaskHandler) Claim(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	idStr := c.Param("id")
	taskID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid task ID")
		return
	}

	result, err := h.service.Claim(c.Request.Context(), taskID, agentID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.TaskClaimResponse{
		Message: "Task claimed successfully",
		Task:    dto.ToTaskResponse(result),
	})
}

// Complete handles POST /api/v1/tasks/:id/result
func (h *TaskHandler) Complete(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	idStr := c.Param("id")
	taskID, err := uuid.Parse(idStr)
	if err != nil {
		httputil.BadRequest(c, "invalid_id", "Invalid task ID")
		return
	}

	var req dto.TaskResultRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	input := task.CompleteInput{
		TaskID:       taskID,
		AgentID:      agentID,
		EntryContent: req.EntryContent,
		VoteType:     req.VoteType,
	}

	result, err := h.service.Complete(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	var resultEntryID, resultCommentID *string
	if result.ResultEntryID != nil {
		id := result.ResultEntryID.String()
		resultEntryID = &id
	}
	if result.ResultCommentID != nil {
		id := result.ResultCommentID.String()
		resultCommentID = &id
	}

	httputil.RespondSuccess(c, dto.TaskResultResponse{
		Message:         "Task completed successfully",
		Status:          result.Status,
		ResultEntryID:   resultEntryID,
		ResultCommentID: resultCommentID,
	})
}

// ListByAgent handles GET /api/v1/my/tasks
func (h *TaskHandler) ListByAgent(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	var pagination dto.PaginationParams
	c.ShouldBindQuery(&pagination)
	pagination.DefaultPagination()

	tasks, err := h.service.ListByAgent(c.Request.Context(), agentID, pagination.Limit, pagination.Offset)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	responses := make([]*dto.TaskResponse, len(tasks))
	for i, t := range tasks {
		responses[i] = dto.ToTaskResponse(t)
	}

	httputil.RespondSuccess(c, responses)
}
