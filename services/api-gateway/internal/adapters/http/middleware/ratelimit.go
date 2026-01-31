package middleware

import (
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// RateLimiter implements a simple in-memory rate limiter
type RateLimiter struct {
	requests map[string]*requestInfo
	mu       sync.RWMutex
	limit    int
	window   time.Duration
	stopCh   chan struct{}
}

type requestInfo struct {
	count     int
	windowEnd time.Time
}

// NewRateLimiter creates a new rate limiter
func NewRateLimiter(limit int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		requests: make(map[string]*requestInfo),
		limit:    limit,
		window:   window,
		stopCh:   make(chan struct{}),
	}

	// Start cleanup goroutine
	go rl.cleanup()

	return rl
}

// Stop stops the rate limiter cleanup goroutine
func (rl *RateLimiter) Stop() {
	close(rl.stopCh)
}

// RateLimit middleware limits requests per IP or agent
func (rl *RateLimiter) RateLimit() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Use agent ID if authenticated, otherwise use IP
		key := c.ClientIP()
		if agentID, exists := c.Get(AgentIDKey); exists {
			if id, ok := agentID.(uuid.UUID); ok {
				key = "agent:" + id.String()
			}
		}

		if !rl.allow(key) {
			requestID := GetRequestID(c)
			c.AbortWithStatusJSON(429, gin.H{
				"success":    false,
				"request_id": requestID,
				"error": gin.H{
					"code":    "rate_limit_exceeded",
					"message": "Too many requests, please try again later",
				},
			})
			return
		}

		c.Next()
	}
}

func (rl *RateLimiter) allow(key string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()

	info, exists := rl.requests[key]
	if !exists || now.After(info.windowEnd) {
		rl.requests[key] = &requestInfo{
			count:     1,
			windowEnd: now.Add(rl.window),
		}
		return true
	}

	if info.count >= rl.limit {
		return false
	}

	info.count++
	return true
}

func (rl *RateLimiter) cleanup() {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			rl.mu.Lock()
			now := time.Now()
			for key, info := range rl.requests {
				if now.After(info.windowEnd) {
					delete(rl.requests, key)
				}
			}
			rl.mu.Unlock()
		case <-rl.stopCh:
			return
		}
	}
}
