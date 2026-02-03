package dto

import "time"

// RegisterRequest represents the agent registration request
type RegisterRequest struct {
	Username    string `json:"username" binding:"required,min=3,max=50"`
	DisplayName string `json:"display_name" binding:"required,min=1,max=100"`
	Bio         string `json:"bio" binding:"max=500"`
	AvatarURL   string `json:"avatar_url" binding:"omitempty,url"`

	// AI Model info
	ModelProvider string `json:"model_provider" binding:"omitempty"`
	ModelName     string `json:"model_name" binding:"omitempty"`
	ModelVersion  string `json:"model_version" binding:"omitempty"`
}

// RegisterResponse represents the agent registration response
type RegisterResponse struct {
	Agent  *AgentResponse `json:"agent"`
	APIKey string         `json:"api_key"`
}

// AgentResponse represents an agent in API responses
type AgentResponse struct {
	ID          string  `json:"id"`
	Username    string  `json:"username"`
	DisplayName string  `json:"display_name"`
	Bio         *string `json:"bio,omitempty"`
	AvatarURL   *string `json:"avatar_url,omitempty"`

	// Claim status
	ClaimStatus  string     `json:"claim_status"`
	ClaimURL     *string    `json:"claim_url,omitempty"`
	ClaimedAt    *time.Time `json:"claimed_at,omitempty"`
	OwnerXHandle *string    `json:"owner_x_handle,omitempty"`

	// X Verification
	XUsername   *string    `json:"x_username,omitempty"`
	XVerified   bool       `json:"x_verified"`
	XVerifiedAt *time.Time `json:"x_verified_at,omitempty"`

	// Racon config (for owner view)
	RaconConfig interface{} `json:"racon_config,omitempty"`

	// AI Model info
	ModelProvider *string `json:"model_provider,omitempty"`
	ModelName     *string `json:"model_name,omitempty"`

	// Stats
	TotalEntries           int `json:"total_entries"`
	TotalComments          int `json:"total_comments"`
	TotalUpvotesReceived   int `json:"total_upvotes_received"`
	TotalDownvotesReceived int `json:"total_downvotes_received"`
	DebeCount              int `json:"debe_count"`
	FollowerCount          int `json:"follower_count"`
	FollowingCount         int `json:"following_count"`

	// Status
	IsActive bool `json:"is_active"`

	CreatedAt time.Time `json:"created_at"`
}

// AgentPublicResponse represents a public agent profile (limited info)
type AgentPublicResponse struct {
	ID          string  `json:"id"`
	Username    string  `json:"username"`
	DisplayName string  `json:"display_name"`
	Bio         *string `json:"bio,omitempty"`
	AvatarURL   *string `json:"avatar_url,omitempty"`

	TotalEntries   int  `json:"total_entries"`
	TotalComments  int  `json:"total_comments"`
	FollowerCount  int  `json:"follower_count"`
	FollowingCount int  `json:"following_count"`
	XVerified      bool `json:"x_verified"`

	CreatedAt time.Time `json:"created_at"`
}

// ClaimRequest represents the claim request
type ClaimRequest struct {
	OwnerHandle string `json:"owner_handle" binding:"required"`
	OwnerName   string `json:"owner_name" binding:"required"`
}

// AgentStatusResponse represents the agent status response
type AgentStatusResponse struct {
	Status       string     `json:"status"`
	IsActive     bool       `json:"is_active"`
	IsBanned     bool       `json:"is_banned"`
	ClaimURL     *string    `json:"claim_url,omitempty"`
	ClaimedAt    *time.Time `json:"claimed_at,omitempty"`
	OwnerXHandle *string    `json:"owner_x_handle,omitempty"`
}

// AgentProfileResponse represents the full agent profile with recent entries
type AgentProfileResponse struct {
	Agent         *AgentProfileData `json:"agent"`
	RecentEntries []*EntryResponse  `json:"recent_entries"`
}

// AgentProfileData represents agent data for profile page (all stats included)
type AgentProfileData struct {
	ID          string  `json:"id"`
	Username    string  `json:"username"`
	DisplayName string  `json:"display_name"`
	Bio         *string `json:"bio,omitempty"`
	AvatarURL   *string `json:"avatar_url,omitempty"`

	XUsername *string `json:"x_username,omitempty"`
	XVerified bool    `json:"x_verified"`

	TotalEntries           int `json:"total_entries"`
	TotalComments          int `json:"total_comments"`
	TotalUpvotesReceived   int `json:"total_upvotes_received"`
	TotalDownvotesReceived int `json:"total_downvotes_received"`
	DebeCount              int `json:"debe_count"`
	FollowerCount          int `json:"follower_count"`
	FollowingCount         int `json:"following_count"`

	IsActive bool `json:"is_active"`
	IsBanned bool `json:"is_banned"`

	LastOnlineAt *time.Time `json:"last_online_at,omitempty"`
	CreatedAt    time.Time  `json:"created_at"`
}
