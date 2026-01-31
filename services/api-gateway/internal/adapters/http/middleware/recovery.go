package middleware

import (
	"log/slog"
	"net/http"
	"runtime/debug"

	"github.com/gin-gonic/gin"
)

// Recovery handles panics and returns a 500 error
func Recovery(logger *slog.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if err := recover(); err != nil {
				// Get request ID for tracing
				requestID := GetRequestID(c)

				// Log the panic with stack trace
				logger.Error("Panic recovered",
					slog.String("request_id", requestID),
					slog.String("method", c.Request.Method),
					slog.String("path", c.Request.URL.Path),
					slog.Any("error", err),
					slog.String("stack", string(debug.Stack())),
				)

				// Return 500 without exposing internal details
				c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{
					"success":    false,
					"request_id": requestID,
					"error": gin.H{
						"code":    "internal_error",
						"message": "An unexpected error occurred",
					},
				})
			}
		}()

		c.Next()
	}
}
