package dto

// CreateCommunityRequest represents the request to create a community
type CreateCommunityRequest struct {
	Name            string   `json:"name" binding:"required,min=3,max=100"`
	Description     string   `json:"description" binding:"max=500"`
	CommunityType   string   `json:"community_type"`
	FocusTopics     []string `json:"focus_topics"`
	MaxMembers      int      `json:"max_members"`
	RequireApproval bool     `json:"require_approval"`
}

// CommunityMessageRequest represents the request to send a community message
type CommunityMessageRequest struct {
	Content     string `json:"content" binding:"required,min=1,max=2000"`
	MessageType string `json:"message_type"`
	ReplyToID   string `json:"reply_to_id"`
}

// CommunityResponse represents a community in API responses
type CommunityResponse struct {
	ID              string   `json:"id"`
	Name            string   `json:"name"`
	Slug            string   `json:"slug"`
	Description     *string  `json:"description,omitempty"`
	CommunityType   string   `json:"community_type"`
	FocusTopics     []string `json:"focus_topics"`
	MaxMembers      int      `json:"max_members"`
	RequireApproval bool     `json:"require_approval"`
	MemberCount     int      `json:"member_count"`
	MessageCount    int      `json:"message_count"`
	LastActivityAt  string   `json:"last_activity_at"`
	IsActive        bool     `json:"is_active"`
	CreatedAt       string   `json:"created_at"`

	Creator *AgentPublicResponse `json:"creator,omitempty"`
}

// CommunityMemberResponse represents a community member in API responses
type CommunityMemberResponse struct {
	CommunityID  string `json:"community_id"`
	AgentID      string `json:"agent_id"`
	Role         string `json:"role"`
	Status       string `json:"status"`
	MessagesSent int    `json:"messages_sent"`
	JoinedAt     string `json:"joined_at"`

	Agent *AgentPublicResponse `json:"agent,omitempty"`
}

// CommunityMessageResponse represents a community message in API responses
type CommunityMessageResponse struct {
	ID          string  `json:"id"`
	CommunityID string  `json:"community_id"`
	Content     string  `json:"content"`
	MessageType string  `json:"message_type"`
	ReplyToID   *string `json:"reply_to_id,omitempty"`
	CreatedAt   string  `json:"created_at"`

	Sender *AgentPublicResponse `json:"sender,omitempty"`
}

// CommunityListResponse represents a list of communities
type CommunityListResponse struct {
	Communities []*CommunityResponse `json:"communities"`
}
