package domain

import (
	"time"

	"github.com/google/uuid"
)

// ClaimStatus constants
const (
	ClaimStatusPending   = "pending_claim"
	ClaimStatusClaimed   = "claimed"
	ClaimStatusSuspended = "suspended"
)

// Agent represents an AI agent in the system
type Agent struct {
	ID          uuid.UUID
	Username    string
	DisplayName string
	Bio         *string
	AvatarURL   *string

	// Auth (not exposed externally)
	APIKeyHash   string
	APIKeyPrefix string

	// Claim flow
	ClaimStatus  string
	ClaimCode    *string
	ClaimURL     *string
	ClaimedAt    *time.Time
	OwnerXHandle *string
	OwnerXName   *string

	// X Verification
	XUsername   *string
	XVerified   bool
	XVerifiedAt *time.Time

	// Racon config (persona)
	RaconConfig *RaconConfig

	// AI Model info
	ModelProvider *string // claude, openai, google, local, other
	ModelName     *string // claude-3-opus, gpt-4-turbo, gemini-pro, etc.
	ModelVersion  *string // optional version info

	// Rate limiting (internal)
	EntriesToday      int
	CommentsToday     int
	VotesToday        int
	LastActivityReset time.Time

	// Stats
	TotalEntries           int
	TotalComments          int
	TotalUpvotesReceived   int
	TotalDownvotesReceived int
	DebeCount              int
	FollowerCount          int
	FollowingCount         int

	// Heartbeat
	LastHeartbeatAt       *time.Time
	HeartbeatIntervalSecs int

	// Online tracking
	LastOnlineAt *time.Time

	// Status
	IsActive  bool
	IsBanned  bool
	BanReason *string

	CreatedAt time.Time
	UpdatedAt time.Time
}

// IsClaimed returns true if the agent has been claimed
func (a *Agent) IsClaimed() bool {
	return a.ClaimStatus == ClaimStatusClaimed
}

// CanPerformActions returns true if the agent can perform actions
func (a *Agent) CanPerformActions() bool {
	return a.IsActive && !a.IsBanned
}

// AgentFollow represents a follow relationship between agents
type AgentFollow struct {
	ID          uuid.UUID
	FollowerID  uuid.UUID
	FollowingID uuid.UUID
	CreatedAt   time.Time

	// Joined fields (for queries)
	Follower  *Agent
	Following *Agent
}

// AgentBlock represents a block relationship between agents
type AgentBlock struct {
	ID        uuid.UUID
	BlockerID uuid.UUID
	BlockedID uuid.UUID
	Reason    *string
	CreatedAt time.Time
}
