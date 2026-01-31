package middleware

import (
	"fmt"
	"log/slog"
	"time"

	"github.com/gin-gonic/gin"
)

// Logger provides structured logging for HTTP requests
func Logger(logger *slog.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		// Process request
		c.Next()

		// Calculate latency
		latency := time.Since(start)
		status := c.Writer.Status()

		// Get request ID
		requestID := GetRequestID(c)

		// Get agent ID if authenticated
		var agentID string
		if id, exists := c.Get("agent_id"); exists {
			switch v := id.(type) {
			case string:
				agentID = v
			case fmt.Stringer:
				agentID = v.String()
			default:
				agentID = fmt.Sprintf("%v", id)
			}
		}

		// Build log attributes
		attrs := []slog.Attr{
			slog.String("request_id", requestID),
			slog.String("method", c.Request.Method),
			slog.String("path", path),
			slog.Int("status", status),
			slog.Duration("latency", latency),
			slog.String("client_ip", c.ClientIP()),
		}

		if query != "" {
			attrs = append(attrs, slog.String("query", query))
		}
		if agentID != "" {
			attrs = append(attrs, slog.String("agent_id", agentID))
		}

		// Log based on status code
		msg := "HTTP request"
		if status >= 500 {
			logger.LogAttrs(c.Request.Context(), slog.LevelError, msg, attrs...)
		} else if status >= 400 {
			logger.LogAttrs(c.Request.Context(), slog.LevelWarn, msg, attrs...)
		} else {
			logger.LogAttrs(c.Request.Context(), slog.LevelInfo, msg, attrs...)
		}
	}
}
