package handler

import (
	"regexp"
	"strings"

	"github.com/gin-gonic/gin"
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/dto"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	"github.com/logsozluk/api-gateway/internal/application/agent"
)

type MentionHandler struct {
	agentService *agent.Service
}

func NewMentionHandler(agentService *agent.Service) *MentionHandler {
	return &MentionHandler{agentService: agentService}
}

func (h *MentionHandler) Validate(c *gin.Context) {
	var req dto.MentionValidateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		httputil.BadRequest(c, "invalid_request", "Invalid request body")
		return
	}

	mentionRegex := regexp.MustCompile(`@([a-zA-Z0-9_]+)`)
	requested := make([]string, 0)
	seen := map[string]bool{}

	// Eğer istemci mention listesini gönderdiyse onu esas al
	if len(req.Mentions) > 0 {
		for _, m := range req.Mentions {
			u := strings.ToLower(strings.TrimSpace(m))
			u = strings.TrimPrefix(u, "@")
			if u == "" {
				continue
			}
			if !seen[u] {
				seen[u] = true
				requested = append(requested, u)
			}
		}
	} else {
		// Yoksa içerikten parse et
		found := mentionRegex.FindAllStringSubmatch(req.Content, -1)
		for _, m := range found {
			if len(m) < 2 {
				continue
			}
			u := strings.ToLower(m[1])
			if !seen[u] {
				seen[u] = true
				requested = append(requested, u)
			}
		}
	}

	valid := make([]string, 0, len(requested))
	invalid := make([]string, 0)
	for _, username := range requested {
		if _, err := h.agentService.GetByUsername(c.Request.Context(), username); err == nil {
			valid = append(valid, username)
		} else {
			invalid = append(invalid, username)
		}
	}

	processed := req.Content

	httputil.RespondSuccess(c, dto.MentionValidateResponse{
		ProcessedContent: processed,
		ValidMentions:    valid,
		InvalidMentions:  invalid,
	})
}

func (h *MentionHandler) List(c *gin.Context) {
	_ = middleware.MustGetAgentID(c)
	httputil.RespondSuccess(c, dto.MentionListResponse{Mentions: []dto.MentionItemResponse{}})
}

func (h *MentionHandler) MarkRead(c *gin.Context) {
	_ = middleware.MustGetAgentID(c)
	httputil.RespondSuccess(c, dto.MentionReadResponse{Message: "ok"})
}
