package middleware

import (
	"os"
	"strings"

	"github.com/gin-gonic/gin"
)

// CORSConfig holds CORS configuration
type CORSConfig struct {
	AllowOrigins     []string
	AllowMethods     []string
	AllowHeaders     []string
	ExposeHeaders    []string
	AllowCredentials bool
	MaxAge           int
}

// DefaultCORSConfig returns default CORS configuration
// WARNING: Uses localhost origins only. For production, use GetCORSConfigFromEnv().
func DefaultCORSConfig() CORSConfig {
	return CORSConfig{
		AllowOrigins: []string{
			"http://localhost:4200",
			"http://localhost:3000",
			"http://127.0.0.1:4200",
			"http://127.0.0.1:3000",
		},
		AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization", "X-Request-ID"},
		ExposeHeaders:    []string{"X-Request-ID"},
		AllowCredentials: false,
		MaxAge:           86400, // 24 hours
	}
}

// GetCORSConfigFromEnv returns CORS config based on environment
// Uses CORS_ALLOWED_ORIGINS env var (comma-separated) or falls back to default
func GetCORSConfigFromEnv() CORSConfig {
	originsEnv := os.Getenv("CORS_ALLOWED_ORIGINS")
	if originsEnv == "" {
		// Development default
		return DefaultCORSConfig()
	}
	
	origins := strings.Split(originsEnv, ",")
	for i := range origins {
		origins[i] = strings.TrimSpace(origins[i])
	}
	
	return ProductionCORSConfig(origins)
}

// ProductionCORSConfig returns CORS config for production environments
func ProductionCORSConfig(allowedOrigins []string) CORSConfig {
	if len(allowedOrigins) == 0 {
		panic("ProductionCORSConfig requires at least one allowed origin")
	}
	return CORSConfig{
		AllowOrigins:     allowedOrigins,
		AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization", "X-Request-ID"},
		ExposeHeaders:    []string{"X-Request-ID"},
		AllowCredentials: true,
		MaxAge:           86400,
	}
}

// CORS middleware handles Cross-Origin Resource Sharing
func CORS(config CORSConfig) gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")

		// Check if origin is allowed
		allowOrigin := "*"
		for _, o := range config.AllowOrigins {
			if o == "*" || o == origin {
				allowOrigin = origin
				break
			}
		}

		c.Header("Access-Control-Allow-Origin", allowOrigin)
		c.Header("Access-Control-Allow-Methods", joinStrings(config.AllowMethods))
		c.Header("Access-Control-Allow-Headers", joinStrings(config.AllowHeaders))
		c.Header("Access-Control-Expose-Headers", joinStrings(config.ExposeHeaders))

		if config.AllowCredentials {
			c.Header("Access-Control-Allow-Credentials", "true")
		}

		// Handle preflight requests
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}

func joinStrings(strs []string) string {
	if len(strs) == 0 {
		return ""
	}
	result := strs[0]
	for i := 1; i < len(strs); i++ {
		result += ", " + strs[i]
	}
	return result
}
