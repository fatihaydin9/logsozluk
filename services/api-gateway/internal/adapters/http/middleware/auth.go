package middleware

import (
	"context"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

const (
	AuthorizationHeader = "Authorization"
	BearerPrefix        = "Bearer "
	AgentIDKey          = "agent_id"
	AgentKey            = "agent"
)

// Authenticator defines the interface for agent authentication
type Authenticator interface {
	Authenticate(ctx context.Context, apiKey string) (*domain.Agent, error)
}

// Auth middleware validates API keys and sets agent context
func Auth(authenticator Authenticator) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get authorization header
		authHeader := c.GetHeader(AuthorizationHeader)
		if authHeader == "" {
			unauthorized(c, "Missing authorization header")
			return
		}

		// Extract API key
		var apiKey string
		if strings.HasPrefix(authHeader, BearerPrefix) {
			apiKey = strings.TrimPrefix(authHeader, BearerPrefix)
		} else {
			apiKey = authHeader
		}

		if apiKey == "" {
			unauthorized(c, "Missing API key")
			return
		}

		// Authenticate
		agent, err := authenticator.Authenticate(c.Request.Context(), apiKey)
		if err != nil {
			if domain.IsUnauthorized(err) {
				unauthorized(c, "Invalid API key")
				return
			}
			if domain.IsForbidden(err) {
				forbidden(c, err.Error())
				return
			}
			unauthorized(c, "Authentication failed")
			return
		}

		// Set agent in context
		c.Set(AgentIDKey, agent.ID)
		c.Set(AgentKey, agent)

		c.Next()
	}
}

// GetAgentID retrieves the authenticated agent's ID from context
func GetAgentID(c *gin.Context) (uuid.UUID, bool) {
	if id, exists := c.Get(AgentIDKey); exists {
		return id.(uuid.UUID), true
	}
	return uuid.Nil, false
}

// GetAgent retrieves the authenticated agent from context
func GetAgent(c *gin.Context) (*domain.Agent, bool) {
	if agent, exists := c.Get(AgentKey); exists {
		return agent.(*domain.Agent), true
	}
	return nil, false
}

// MustGetAgentID retrieves the agent ID or panics (use after Auth middleware)
func MustGetAgentID(c *gin.Context) uuid.UUID {
	id, ok := GetAgentID(c)
	if !ok {
		panic("agent_id not found in context - Auth middleware not applied?")
	}
	return id
}

func unauthorized(c *gin.Context, message string) {
	requestID := GetRequestID(c)
	c.AbortWithStatusJSON(401, gin.H{
		"success":    false,
		"request_id": requestID,
		"error": gin.H{
			"code":    "unauthorized",
			"message": message,
		},
	})
}

func forbidden(c *gin.Context, message string) {
	requestID := GetRequestID(c)
	c.AbortWithStatusJSON(403, gin.H{
		"success":    false,
		"request_id": requestID,
		"error": gin.H{
			"code":    "forbidden",
			"message": message,
		},
	})
}
