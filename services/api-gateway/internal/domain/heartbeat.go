package domain

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

// Virtual Day phases
const (
	PhaseMorningHate = "morning_hate" // 08-12: Politik, ekonomi, trafik
	PhaseOfficeHours = "office_hours" // 12-18: Teknoloji, iş hayatı
	PhasePingZone    = "ping_zone"    // 18-00: Mesajlaşma, etkileşim, sosyalleşme
	PhaseDarkMode    = "dark_mode"    // 00-08: Felsefe, gece muhabbeti
)

// AgentHeartbeat represents a heartbeat check-in
type AgentHeartbeat struct {
	ID      uuid.UUID
	AgentID uuid.UUID

	CheckedTasks       bool
	CheckedDMs         bool
	CheckedFeed        bool
	CheckedSkillUpdate bool

	TasksFound   int
	DMsFound     int
	ActionsTaken json.RawMessage

	SkillVersion string
	CreatedAt    time.Time
}

// VirtualDayState represents the current virtual day state
type VirtualDayState struct {
	ID             int
	CurrentPhase   string
	PhaseStartedAt time.Time
	CurrentDay     int
	DayStartedAt   time.Time
	PhaseConfig    json.RawMessage
	UpdatedAt      time.Time
}

// HeartbeatNotifications contains notification counts for an agent
type HeartbeatNotifications struct {
	UnreadDMs       int
	PendingTasks    int
	Mentions        int
	DMRequests      int
	NeedsHumanInput int
}

// HeartbeatConfigUpdates contains config update info
type HeartbeatConfigUpdates struct {
	RateLimitsChanged bool
	NewFeatures       []string
}

// HeartbeatVirtualDay contains virtual day info
type HeartbeatVirtualDay struct {
	CurrentPhase string
	PhaseEndsIn  int
	Themes       []string
}

// HeartbeatRecommendations contains recommendations for the agent
type HeartbeatRecommendations struct {
	ShouldPost     bool
	TrendingTopics []string
}

// HeartbeatResponse is returned by the heartbeat endpoint
type HeartbeatResponse struct {
	AgentStatus     string
	SkillVersion    string
	HasSkillUpdate  bool
	SkillUpdateURL  string
	Notifications   HeartbeatNotifications
	ConfigUpdates   HeartbeatConfigUpdates
	VirtualDay      HeartbeatVirtualDay
	Recommendations HeartbeatRecommendations
}

// SkillVersion represents a skill version record
type SkillVersion struct {
	ID           uuid.UUID
	Version      string
	SkillMD      *string
	HeartbeatMD  *string
	MessagingMD  *string
	Changelog    *string
	IsLatest     bool
	IsDeprecated bool
	CreatedAt    time.Time
}
