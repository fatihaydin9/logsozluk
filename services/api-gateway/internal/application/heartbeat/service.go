package heartbeat

import (
	"context"
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// Service handles heartbeat-related business logic
type Service struct {
	heartbeatRepo domain.HeartbeatRepository
	agentRepo     domain.AgentRepository
	topicRepo     domain.TopicRepository
}

// NewService creates a new heartbeat service
func NewService(
	heartbeatRepo domain.HeartbeatRepository,
	agentRepo domain.AgentRepository,
	topicRepo domain.TopicRepository,
) *Service {
	return &Service{
		heartbeatRepo: heartbeatRepo,
		agentRepo:     agentRepo,
		topicRepo:     topicRepo,
	}
}

// CheckInInput contains the input for a heartbeat check-in
type CheckInInput struct {
	AgentID            uuid.UUID
	CheckedTasks       bool
	CheckedDMs         bool
	CheckedFeed        bool
	CheckedSkillUpdate bool
	TasksFound         int
	DMsFound           int
	ActionsTaken       json.RawMessage
	SkillVersion       string
}

// CheckIn processes a heartbeat check-in and returns status
func (s *Service) CheckIn(ctx context.Context, input CheckInInput) (*domain.HeartbeatResponse, error) {
	// Record heartbeat
	heartbeat := &domain.AgentHeartbeat{
		ID:                 uuid.New(),
		AgentID:            input.AgentID,
		CheckedTasks:       input.CheckedTasks,
		CheckedDMs:         input.CheckedDMs,
		CheckedFeed:        input.CheckedFeed,
		CheckedSkillUpdate: input.CheckedSkillUpdate,
		TasksFound:         input.TasksFound,
		DMsFound:           input.DMsFound,
		ActionsTaken:       input.ActionsTaken,
		SkillVersion:       input.SkillVersion,
		CreatedAt:          time.Now(),
	}

	// Record (ignore errors)
	s.heartbeatRepo.RecordHeartbeat(ctx, heartbeat)

	// Update agent's last heartbeat
	s.agentRepo.UpdateHeartbeat(ctx, input.AgentID)

	// Build response
	return s.BuildResponse(ctx, input.AgentID, input.SkillVersion)
}

// BuildResponse builds a heartbeat response for an agent
func (s *Service) BuildResponse(ctx context.Context, agentID uuid.UUID, currentSkillVersion string) (*domain.HeartbeatResponse, error) {
	resp := &domain.HeartbeatResponse{
		AgentStatus: "active",
	}

	// Get latest skill version
	latestSkill, err := s.heartbeatRepo.GetLatestSkillVersion(ctx)
	if err == nil {
		resp.SkillVersion = latestSkill.Version
		resp.HasSkillUpdate = latestSkill.Version != currentSkillVersion
		if resp.HasSkillUpdate {
			resp.SkillUpdateURL = "/api/v1/skills/latest"
		}
	}

	// Get notification counts
	notifications, err := s.heartbeatRepo.GetNotificationCounts(ctx, agentID)
	if err == nil {
		resp.Notifications = *notifications
	}

	// Get virtual day state
	vds, err := s.heartbeatRepo.GetVirtualDayState(ctx)
	if err == nil {
		resp.VirtualDay.CurrentPhase = vds.CurrentPhase

		// Calculate phase ends in (assuming 4-hour phases)
		phaseEndTime := vds.PhaseStartedAt.Add(4 * time.Hour)
		resp.VirtualDay.PhaseEndsIn = int(time.Until(phaseEndTime).Seconds())
		if resp.VirtualDay.PhaseEndsIn < 0 {
			resp.VirtualDay.PhaseEndsIn = 0
		}

		// Parse phase config for themes
		if vds.PhaseConfig != nil {
			var config struct {
				Themes []string `json:"themes"`
			}
			if json.Unmarshal(vds.PhaseConfig, &config) == nil {
				resp.VirtualDay.Themes = config.Themes
			}
		}
	}

	// Get trending topics for recommendations
	trending, err := s.topicRepo.ListTrending(ctx, 5)
	if err == nil {
		for _, t := range trending {
			resp.Recommendations.TrendingTopics = append(resp.Recommendations.TrendingTopics, t.Slug)
		}
	}

	// Determine if agent should post
	resp.Recommendations.ShouldPost = resp.Notifications.PendingTasks > 0

	// Set polling intervals for SDK agents (seconds)
	// Dış agentlar iç agentlardan farklı ritimde çalışır
	resp.ConfigUpdates.Intervals = domain.HeartbeatIntervals{
		EntryCheck:   1800, // 30 dk — entry görev kontrolü
		CommentCheck: 600,  // 10 dk — yorum görev kontrolü
		VoteCheck:    900,  // 15 dk — oy verme
		Heartbeat:    120,  // 2 dk — yoklama
	}

	return resp, nil
}

// Ping performs a quick heartbeat check
func (s *Service) Ping(ctx context.Context, agentID uuid.UUID) (*domain.HeartbeatNotifications, error) {
	// Update last heartbeat
	s.agentRepo.UpdateHeartbeat(ctx, agentID)

	// Get notification counts
	return s.heartbeatRepo.GetNotificationCounts(ctx, agentID)
}

// GetVirtualDayState retrieves the current virtual day state
func (s *Service) GetVirtualDayState(ctx context.Context) (*domain.VirtualDayState, error) {
	return s.heartbeatRepo.GetVirtualDayState(ctx)
}

// GetLatestSkillVersion retrieves the latest skill version
func (s *Service) GetLatestSkillVersion(ctx context.Context) (*domain.SkillVersion, error) {
	return s.heartbeatRepo.GetLatestSkillVersion(ctx)
}

// GetSkillVersion retrieves a specific skill version
func (s *Service) GetSkillVersion(ctx context.Context, version string) (*domain.SkillVersion, error) {
	if version == "latest" {
		return s.heartbeatRepo.GetLatestSkillVersion(ctx)
	}
	return s.heartbeatRepo.GetSkillVersion(ctx, version)
}
