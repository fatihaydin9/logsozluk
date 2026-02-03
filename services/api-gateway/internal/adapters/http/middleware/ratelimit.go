package middleware

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

// RateLimiter implements a rate limiter with optional Redis backend
// If Redis is configured, it uses Redis for distributed rate limiting (horizontal scaling)
// Otherwise falls back to in-memory rate limiting (single instance only)
type RateLimiter struct {
	// In-memory fallback
	requests map[string]*requestInfo
	mu       sync.RWMutex
	
	// Redis backend (optional)
	redis    *redis.Client
	
	// Configuration
	limit    int
	window   time.Duration
	stopCh   chan struct{}
}

type requestInfo struct {
	count     int
	windowEnd time.Time
}

// NewRateLimiter creates a new in-memory rate limiter (single instance only)
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

// NewRedisRateLimiter creates a Redis-backed rate limiter (horizontal scaling support)
// Also initializes in-memory fallback for fail-closed behavior when Redis is unavailable
func NewRedisRateLimiter(redisClient *redis.Client, limit int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		requests: make(map[string]*requestInfo), // Fallback for Redis failures
		redis:    redisClient,
		limit:    limit,
		window:   window,
		stopCh:   make(chan struct{}),
	}

	// Start cleanup goroutine for in-memory fallback
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
	// Use Redis if available (horizontal scaling)
	if rl.redis != nil {
		return rl.allowRedis(key)
	}
	
	// Fallback to in-memory (single instance only)
	return rl.allowInMemory(key)
}

func (rl *RateLimiter) allowRedis(key string) bool {
	ctx := context.Background()
	redisKey := fmt.Sprintf("ratelimit:%s", key)

	// Use Redis INCR with expiry for atomic rate limiting
	count, err := rl.redis.Incr(ctx, redisKey).Result()
	if err != nil {
		// Redis error - fail-closed: fall back to in-memory rate limiting
		// This ensures rate limiting continues even when Redis is unavailable
		return rl.allowInMemory(key)
	}

	// Set expiry on first request
	if count == 1 {
		rl.redis.Expire(ctx, redisKey, rl.window)
	}

	return count <= int64(rl.limit)
}

func (rl *RateLimiter) allowInMemory(key string) bool {
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
