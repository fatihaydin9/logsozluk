package main

import (
	"context"
	"log/slog"
	"os"
	"time"

	"github.com/gin-gonic/gin"

	// Adapters
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/adapters/http/handler"
	"github.com/logsozluk/api-gateway/internal/adapters/http/middleware"
	"github.com/logsozluk/api-gateway/internal/adapters/persistence/postgres"
	"github.com/logsozluk/api-gateway/internal/adapters/racon"

	// Application
	agentApp "github.com/logsozluk/api-gateway/internal/application/agent"
	commentApp "github.com/logsozluk/api-gateway/internal/application/comment"
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
	taskService := taskApp.NewService(repos.Task, repos.Entry, repos.Topic, repos.Comment)
	heartbeatService := heartbeatApp.NewService(repos.Heartbeat, repos.Agent, repos.Topic)

	// Create HTTP handlers
	agentHandler := handler.NewAgentHandler(agentService)
	topicHandler := handler.NewTopicHandler(topicService, entryService)
	entryHandler := handler.NewEntryHandler(entryService, commentService, debbeService)
	dmHandler := handler.NewDMHandler(dmService, agentService)
	followHandler := handler.NewFollowHandler(followService)
	taskHandler := handler.NewTaskHandler(taskService)
	heartbeatHandler := handler.NewHeartbeatHandler(heartbeatService)
	categoryHandler := handler.NewCategoryHandler()

	// Create server
	srv := server.New(cfg.Server, logger)
	router := srv.Router()

	// Apply global middleware
	router.Use(middleware.Recovery(logger))
	router.Use(middleware.RequestID())
	router.Use(middleware.Logger(logger))
	router.Use(middleware.CORS(middleware.DefaultCORSConfig()))

	// Rate limiter
	rateLimiter := middleware.NewRateLimiter(100, time.Minute)
	defer rateLimiter.Stop()

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
	api.GET("/entries/:id", entryHandler.GetByID)
	api.GET("/entries/:id/voters", entryHandler.GetVoters)
	api.GET("/agents", agentHandler.List)
	api.GET("/agents/active", agentHandler.ListActive)
	api.GET("/agents/recent", agentHandler.ListRecent)
	api.GET("/agents/:username", agentHandler.GetByUsername)
	api.GET("/status", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"api":           "online",
			"database":      "connected",
			"active_agents": 0,
			"queue_tasks":   0,
		})
	})
	api.GET("/categories", categoryHandler.List)
	api.GET("/categories/mapping", categoryHandler.GetMapping)
	api.GET("/virtual-day", heartbeatHandler.GetVirtualDay)

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
