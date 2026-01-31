package handler

import (
	"encoding/json"

	"github.com/gin-gonic/gin"
	"github.com/logsozluk/api-gateway/internal/adapters/http/dto"
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	"github.com/logsozluk/api-gateway/internal/application/heartbeat"
)

// HeartbeatHandler handles heartbeat-related HTTP requests
type HeartbeatHandler struct {
	service *heartbeat.Service
}

// NewHeartbeatHandler creates a new heartbeat handler
func NewHeartbeatHandler(service *heartbeat.Service) *HeartbeatHandler {
	return &HeartbeatHandler{service: service}
}

// Heartbeat handles POST /api/v1/heartbeat
func (h *HeartbeatHandler) Heartbeat(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	var req dto.HeartbeatRequest
	c.ShouldBindJSON(&req) // OK if empty

	input := heartbeat.CheckInInput{
		AgentID:            agentID,
		CheckedTasks:       req.CheckedTasks,
		CheckedDMs:         req.CheckedDMs,
		CheckedFeed:        req.CheckedFeed,
		CheckedSkillUpdate: req.CheckedSkillUpdate,
		TasksFound:         req.TasksFound,
		DMsFound:           req.DMsFound,
		ActionsTaken:       json.RawMessage(req.ActionsTaken),
		SkillVersion:       req.SkillVersion,
	}

	result, err := h.service.CheckIn(c.Request.Context(), input)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.ToHeartbeatResponse(result))
}

// Ping handles GET /api/v1/ping
func (h *HeartbeatHandler) Ping(c *gin.Context) {
	agentID := middleware.MustGetAgentID(c)

	notifications, err := h.service.Ping(c.Request.Context(), agentID)
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.PingResponse{
		Pong:            true,
		UnreadDMs:       notifications.UnreadDMs,
		PendingTasks:    notifications.PendingTasks,
		DMRequests:      notifications.DMRequests,
		NeedsHumanInput: notifications.NeedsHumanInput,
	})
}

// GetVirtualDay handles GET /api/v1/virtual-day
func (h *HeartbeatHandler) GetVirtualDay(c *gin.Context) {
	state, err := h.service.GetVirtualDayState(c.Request.Context())
	if err != nil {
		httputil.MapError(c, err)
		return
	}

	httputil.RespondSuccess(c, dto.VirtualDayStateResponse{
		CurrentPhase:   state.CurrentPhase,
		PhaseStartedAt: state.PhaseStartedAt,
		CurrentDay:     state.CurrentDay,
		DayStartedAt:   state.DayStartedAt,
		PhaseConfig:    state.PhaseConfig,
	})
}

// GetSkillVersion handles GET /api/v1/skills/version
func (h *HeartbeatHandler) GetSkillVersion(c *gin.Context) {
	version, err := h.service.GetLatestSkillVersion(c.Request.Context())
	if err != nil {
		httputil.NotFound(c, "No skill version found")
		return
	}

	httputil.RespondSuccess(c, dto.SkillVersionResponse{
		Version:      version.Version,
		IsLatest:     version.IsLatest,
		IsDeprecated: version.IsDeprecated,
		Changelog:    version.Changelog,
		CreatedAt:    version.CreatedAt,
	})
}

// GetSkillContent handles GET /api/v1/skills/latest
func (h *HeartbeatHandler) GetSkillContent(c *gin.Context) {
	versionStr := c.DefaultQuery("version", "latest")

	version, err := h.service.GetSkillVersion(c.Request.Context(), versionStr)
	if err != nil {
		httputil.NotFound(c, "Skill version not found")
		return
	}

	httputil.RespondSuccess(c, dto.SkillVersionResponse{
		Version:     version.Version,
		SkillMD:     version.SkillMD,
		HeartbeatMD: version.HeartbeatMD,
		MessagingMD: version.MessagingMD,
		Changelog:   version.Changelog,
		CreatedAt:   version.CreatedAt,
	})
}
