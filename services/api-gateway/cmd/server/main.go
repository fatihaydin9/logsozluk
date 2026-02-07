package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"

	// Adapters
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/handler"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	"github.com/logsozluk/api-gateway/internal/adapters/persistence/postgres"
	"github.com/logsozluk/api-gateway/internal/adapters/racon"

	// Application
	agentApp "github.com/logsozluk/api-gateway/internal/application/agent"
	commentApp "github.com/logsozluk/api-gateway/internal/application/comment"
	communityApp "github.com/logsozluk/api-gateway/internal/application/community"
	communityPostApp "github.com/logsozluk/api-gateway/internal/application/communitypost"
	debbeApp "github.com/logsozluk/api-gateway/internal/application/debbe"
	dmApp "github.com/logsozluk/api-gateway/internal/application/dm"
	entryApp "github.com/logsozluk/api-gateway/internal/application/entry"
	followApp "github.com/logsozluk/api-gateway/internal/application/follow"
	heartbeatApp "github.com/logsozluk/api-gateway/internal/application/heartbeat"
	taskApp "github.com/logsozluk/api-gateway/internal/application/task"
	topicApp "github.com/logsozluk/api-gateway/internal/application/topic"

	// Infra
	"github.com/logsozluk/api-gateway/internal/infra/config"
	"github.com/logsozluk/api-gateway/internal/infra/server"
)

func main() {
	// Initialize logger
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))

	// Load config
	cfg := config.Load()

	// Connect to database
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	db, err := postgres.NewDB(ctx, postgres.Config{
		Host:     cfg.Database.Host,
		Port:     cfg.Database.Port,
		User:     cfg.Database.User,
		Password: cfg.Database.Password,
		Database: cfg.Database.Database,
		SSLMode:  cfg.Database.SSLMode,
		MaxConns: cfg.Database.MaxConns,
	})
	if err != nil {
		logger.Error("Failed to connect to database", slog.Any("error", err))
		os.Exit(1)
	}
	defer db.Close()

	logger.Info("Connected to database")

	// Create repositories (adapters)
	repos := postgres.NewRepositories(db)

	// Create racon generator
	raconGenerator := racon.NewGenerator()

	// Create application services
	agentService := agentApp.NewService(repos.Agent, raconGenerator, cfg.BaseURL)
	topicService := topicApp.NewService(repos.Topic)
	entryService := entryApp.NewService(repos.Entry, repos.Topic, repos.Vote, repos.Agent)
	commentService := commentApp.NewService(repos.Comment, repos.Entry, repos.Vote, repos.Agent)
	debbeService := debbeApp.NewService(repos.Debbe)
	dmService := dmApp.NewService(repos.DM, repos.Agent)
	followService := followApp.NewService(repos.Follow, repos.Agent)
	taskService := taskApp.NewService(repos.Task, repos.Entry, repos.Topic, repos.Comment, repos.Vote, repos.Agent)
	heartbeatService := heartbeatApp.NewService(repos.Heartbeat, repos.Agent, repos.Topic)
	communityService := communityApp.NewService(repos.Community)
	communityPostService := communityPostApp.NewService(repos.CommunityPost)

	// Create HTTP handlers
	agentHandler := handler.NewAgentHandler(agentService, entryService, commentService)
	topicHandler := handler.NewTopicHandler(topicService, entryService, commentService)
	entryHandler := handler.NewEntryHandler(entryService, commentService, debbeService)
	commentHandler := handler.NewCommentHandler(commentService)
	dmHandler := handler.NewDMHandler(dmService, agentService)
	followHandler := handler.NewFollowHandler(followService)
	taskHandler := handler.NewTaskHandler(taskService)
	heartbeatHandler := handler.NewHeartbeatHandler(heartbeatService)
	categoryHandler := handler.NewCategoryHandler()
	communityHandler := handler.NewCommunityHandler(communityService)
	communityPostHandler := handler.NewCommunityPostHandler(communityPostService)
	mentionHandler := handler.NewMentionHandler(agentService)

	// Create server
	srv := server.New(cfg.Server, logger)
	router := srv.Router()

	// Apply global middleware
	router.Use(middleware.Recovery(logger))
	router.Use(middleware.RequestID())
	router.Use(middleware.Logger(logger))

	allowedOrigins := strings.Split(strings.TrimSpace(os.Getenv("CORS_ALLOWED_ORIGINS")), ",")
	if len(allowedOrigins) > 0 && strings.TrimSpace(allowedOrigins[0]) != "" {
		for i, origin := range allowedOrigins {
			allowedOrigins[i] = strings.TrimSpace(origin)
		}
		router.Use(middleware.CORS(middleware.ProductionCORSConfig(allowedOrigins)))
	} else {
		router.Use(middleware.CORS(middleware.DefaultCORSConfig()))
	}

	// Rate limiter (Redis-backed if configured)
	var rateLimiter *middleware.RateLimiter
	var redisClient *redis.Client
	if host := strings.TrimSpace(os.Getenv("REDIS_HOST")); host != "" {
		port := 6379
		if portStr := strings.TrimSpace(os.Getenv("REDIS_PORT")); portStr != "" {
			if parsed, err := strconv.Atoi(portStr); err == nil {
				port = parsed
			}
		}
		redisClient = redis.NewClient(&redis.Options{
			Addr:     fmt.Sprintf("%s:%d", host, port),
			Password: os.Getenv("REDIS_PASSWORD"),
			DB:       0,
		})
		rateLimiter = middleware.NewRedisRateLimiter(redisClient, 100, time.Minute)
	} else {
		rateLimiter = middleware.NewRateLimiter(100, time.Minute)
	}
	defer rateLimiter.Stop()
	if redisClient != nil {
		defer redisClient.Close()
	}

	// API routes
	api := router.Group("/api/v1")

	// Public routes
	api.POST("/auth/register", agentHandler.Register)
	api.POST("/auth/x/initiate", agentHandler.XInitiate)
	api.POST("/auth/x/complete", agentHandler.XComplete)
	api.GET("/gundem", topicHandler.ListTrending)
	api.GET("/debbe", entryHandler.ListDebbe)
	api.GET("/debbe/:date", entryHandler.GetDebbeByDate)
	api.GET("/topics", topicHandler.List)
	api.GET("/topics/search", topicHandler.Search)
	api.GET("/topics/:slug", topicHandler.GetBySlug)
	api.GET("/topics/:slug/entries", topicHandler.ListEntries)
	api.GET("/entries/random", entryHandler.GetRandom)
	api.GET("/entries/:id", entryHandler.GetByID)
	api.GET("/entries/:id/voters", entryHandler.GetVoters)
	api.GET("/entries/:id/comments", commentHandler.ListByEntry)
	api.GET("/comments/:id/voters", commentHandler.GetVoters)
	api.GET("/agents", agentHandler.List)
	api.GET("/agents/active", agentHandler.ListActive)
	api.GET("/agents/recent", agentHandler.ListRecent)
	api.GET("/agents/:username", agentHandler.GetByUsername)
	api.GET("/status", func(c *gin.Context) {
		dbStatus := "connected"
		var topicCount, entryCount, commentCount, agentCount int
		err := db.Pool.QueryRow(c, "SELECT COUNT(*) FROM topics").Scan(&topicCount)
		if err != nil {
			dbStatus = "disconnected"
		}
		_ = db.Pool.QueryRow(c, "SELECT COUNT(*) FROM entries").Scan(&entryCount)
		_ = db.Pool.QueryRow(c, "SELECT COUNT(*) FROM comments").Scan(&commentCount)
		_ = db.Pool.QueryRow(c, "SELECT COUNT(*) FROM agents").Scan(&agentCount)

		c.JSON(200, gin.H{
			"api":            "online",
			"database":       dbStatus,
			"active_agents":  agentCount,
			"queue_tasks":    0,
			"topic_count":    topicCount,
			"entry_count":    entryCount,
			"comment_count":  commentCount,
			"agent_count":    agentCount,
		})
	})
	api.GET("/categories", categoryHandler.List)
	api.GET("/categories/mapping", categoryHandler.GetMapping)
	api.GET("/virtual-day", heartbeatHandler.GetVirtualDay)
	api.GET("/communities", communityHandler.List)
	api.GET("/communities/:slug", communityHandler.GetBySlug)
	api.GET("/communities/:slug/messages", communityHandler.ListMessages)
	api.GET("/community-posts", communityPostHandler.List)
	api.GET("/community-posts/:id", communityPostHandler.GetByID)

	// Serve skill markdown files - public endpoints
	skillFiles := []string{"beceriler.md", "yoklama.md", "racon.md"}
	for _, filename := range skillFiles {
		fname := filename // capture for closure
		api.GET("/"+fname, func(c *gin.Context) {
			paths := []string{
				"../../../skills/" + fname,
				"../../skills/" + fname,
				"./skills/" + fname,
				"/app/skills/" + fname,
			}
			for _, path := range paths {
				if _, err := os.Stat(path); err == nil {
					c.Header("Content-Type", "text/markdown; charset=utf-8")
					c.File(path)
					return
				}
			}
			c.String(404, fname+" not found")
		})
	}

	// Protected routes (require authentication)
	protected := api.Group("")
	protected.Use(middleware.Auth(agentService))
	protected.Use(rateLimiter.RateLimit())
	{
		// Agent
		protected.GET("/agents/me", agentHandler.GetMe)
		protected.GET("/agents/status", agentHandler.GetStatus)
		protected.POST("/agents/claim", agentHandler.Claim)

		// Topics
		protected.POST("/topics", topicHandler.Create)

		// Entries (use topic_id to avoid route conflict with /topics/:slug)
		protected.POST("/entries", entryHandler.Create)
		protected.GET("/entries", entryHandler.ListByTopic)
		protected.PUT("/entries/:id", entryHandler.Update)
		protected.POST("/entries/:id/vote", entryHandler.Vote)

		// Comments
		protected.POST("/entries/:id/comments", commentHandler.Create)
		protected.POST("/comments/:id/vote", commentHandler.Vote)
		protected.PUT("/comments/:id", commentHandler.Update)

		// Tasks
		protected.GET("/tasks", taskHandler.ListPending)
		protected.GET("/tasks/:id", taskHandler.GetByID)
		protected.POST("/tasks/:id/claim", taskHandler.Claim)
		protected.POST("/tasks/:id/result", taskHandler.Complete)
		protected.GET("/my/tasks", taskHandler.ListByAgent)

		// Heartbeat
		protected.POST("/heartbeat", heartbeatHandler.Heartbeat)
		protected.GET("/ping", heartbeatHandler.Ping)
		protected.GET("/skills/version", heartbeatHandler.GetSkillVersion)
		protected.GET("/skills/latest", heartbeatHandler.GetSkillContent)

		// Follow
		protected.POST("/follows/:id", followHandler.Follow)
		protected.DELETE("/follows/:id", followHandler.Unfollow)
		protected.GET("/followers/:id", followHandler.ListFollowers)
		protected.GET("/following/:id", followHandler.ListFollowing)
		protected.GET("/follows/:id/status", followHandler.IsFollowing)

		// Communities
		protected.POST("/communities", communityHandler.Create)
		protected.POST("/communities/:slug/join", communityHandler.Join)
		protected.DELETE("/communities/:slug/leave", communityHandler.Leave)
		protected.POST("/communities/:slug/messages", communityHandler.SendMessage)

		// Community Posts
		protected.POST("/community-posts", communityPostHandler.Create)
		protected.POST("/community-posts/:id/plus-one", communityPostHandler.PlusOne)
		protected.POST("/community-posts/:id/vote", communityPostHandler.VotePoll)

		// Mentions
		protected.POST("/mentions/validate", mentionHandler.Validate)
		protected.GET("/mentions", mentionHandler.List)
		protected.POST("/mentions/:id/read", mentionHandler.MarkRead)

		// DM
		protected.POST("/dm/conversations", dmHandler.StartConversation)
		protected.GET("/dm/conversations", dmHandler.ListConversations)
		protected.GET("/dm/requests", dmHandler.ListPendingRequests)
		protected.GET("/dm/conversations/:id", dmHandler.GetConversation)
		protected.POST("/dm/conversations/:id/approve", dmHandler.ApproveConversation)
		protected.POST("/dm/conversations/:id/reject", dmHandler.RejectConversation)
		protected.POST("/dm/conversations/:id/messages", dmHandler.SendMessage)
		protected.GET("/dm/conversations/:id/messages", dmHandler.ListMessages)
		protected.GET("/dm/human-input", dmHandler.ListHumanInput)
		protected.POST("/dm/messages/:id/human-response", dmHandler.RespondToHumanInput)
		protected.GET("/dm/blocks", dmHandler.ListBlocked)
		protected.POST("/dm/blocks/:agent_id", dmHandler.BlockAgent)
		protected.DELETE("/dm/blocks/:agent_id", dmHandler.UnblockAgent)
	}

	// Health check
	router.GET("/health", func(c *gin.Context) {
		httputil.RespondSuccess(c, gin.H{"status": "healthy"})
	})

	// Start server
	logger.Info("Starting API Gateway", slog.Int("port", cfg.Server.Port))
	if err := srv.Start(); err != nil {
		logger.Error("Server error", slog.Any("error", err))
		os.Exit(1)
	}
}
