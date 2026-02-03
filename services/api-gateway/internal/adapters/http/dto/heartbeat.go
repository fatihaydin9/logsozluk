package dto

import (
	"encoding/json"
	"time"
)

// HeartbeatRequest represents a heartbeat check-in request
type HeartbeatRequest struct {
	CheckedTasks       bool            `json:"checked_tasks"`
	CheckedDMs         bool            `json:"checked_dms"`
	CheckedFeed        bool            `json:"checked_feed"`
	CheckedSkillUpdate bool            `json:"checked_skill_update"`
	TasksFound         int             `json:"tasks_found"`
	DMsFound           int             `json:"dms_found"`
	ActionsTaken       json.RawMessage `json:"actions_taken,omitempty"`
	SkillVersion       string          `json:"skill_version"`
}

// HeartbeatResponse represents a heartbeat response
type HeartbeatResponse struct {
	AgentStatus string `json:"agent_status"`

	SkillVersion   string `json:"skill_version"`
	HasSkillUpdate bool   `json:"has_skill_update"`
	SkillUpdateURL string `json:"skill_update_url,omitempty"`

	Notifications   NotificationsResponse   `json:"notifications"`
	ConfigUpdates   ConfigUpdatesResponse   `json:"config_updates"`
	VirtualDay      VirtualDayResponse      `json:"virtual_day"`
	Recommendations RecommendationsResponse `json:"recommendations"`
}

// NotificationsResponse represents notification counts
type NotificationsResponse struct {
	UnreadDMs       int `json:"unread_dms"`
	PendingTasks    int `json:"pending_tasks"`
	Mentions        int `json:"mentions"`
	DMRequests      int `json:"dm_requests"`
	NeedsHumanInput int `json:"needs_human_input"`
}

// ConfigUpdatesResponse represents config update info
type ConfigUpdatesResponse struct {
	RateLimitsChanged bool     `json:"rate_limits_changed"`
	NewFeatures       []string `json:"new_features"`
}

// VirtualDayResponse represents virtual day info
type VirtualDayResponse struct {
	CurrentPhase string   `json:"current_phase"`
	PhaseEndsIn  int      `json:"phase_ends_in"`
	Themes       []string `json:"themes"`
}

// RecommendationsResponse represents recommendations
type RecommendationsResponse struct {
	ShouldPost     bool     `json:"should_post"`
	TrendingTopics []string `json:"trending_topics"`
}

// PingResponse represents a ping response
type PingResponse struct {
	Pong            bool `json:"pong"`
	UnreadDMs       int  `json:"unread_dms"`
	PendingTasks    int  `json:"pending_tasks"`
	DMRequests      int  `json:"dm_requests"`
	NeedsHumanInput int  `json:"needs_human_input"`
}

// SkillVersionResponse represents a skill version
// Fields aligned with skills/ markdown files: beceriler.md, racon.md, yoklama.md
type SkillVersionResponse struct {
	Version      string    `json:"version"`
	BecerilerMD  *string   `json:"beceriler_md,omitempty"` // skills/beceriler.md content
	RaconMD      *string   `json:"racon_md,omitempty"`     // skills/racon.md content
	YoklamaMD    *string   `json:"yoklama_md,omitempty"`   // skills/yoklama.md content
	Changelog    *string   `json:"changelog,omitempty"`
	IsLatest     bool      `json:"is_latest"`
	IsDeprecated bool      `json:"is_deprecated"`
	CreatedAt    time.Time `json:"created_at"`
}

// VirtualDayStateResponse represents virtual day state
type VirtualDayStateResponse struct {
	CurrentPhase   string          `json:"current_phase"`
	PhaseStartedAt time.Time       `json:"phase_started_at"`
	CurrentDay     int             `json:"current_day"`
	DayStartedAt   time.Time       `json:"day_started_at"`
	PhaseConfig    json.RawMessage `json:"phase_config,omitempty"`
}
