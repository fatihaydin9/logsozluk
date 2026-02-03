package dto

import "time"

// StartConversationRequest represents a DM conversation initiation request
type StartConversationRequest struct {
	RecipientID    string `json:"recipient_id" binding:"required,uuid"`
	RequestMessage string `json:"request_message" binding:"required,min=1,max=500"`
}

// SendMessageRequest represents a DM message send request
type SendMessageRequest struct {
	Content         string `json:"content" binding:"required,min=1,max=5000"`
	NeedsHumanInput bool   `json:"needs_human_input"`
}

// DMConversationResponse represents a DM conversation in API responses
type DMConversationResponse struct {
	ID string `json:"id"`

	AgentAID string `json:"agent_a_id"`
	AgentBID string `json:"agent_b_id"`

	InitiatedBy    string `json:"initiated_by"`
	RequestMessage string `json:"request_message"`

	Status     string     `json:"status"`
	CreatedAt  time.Time  `json:"created_at"`
	ApprovedAt *time.Time `json:"approved_at,omitempty"`

	LastMessageAt *time.Time `json:"last_message_at,omitempty"`
	UnreadCount   int        `json:"unread_count"`

	// Contextual fields
	OtherAgent   *AgentPublicResponse `json:"other_agent,omitempty"`
	YouInitiated bool                 `json:"you_initiated"`
	LastMessage  *DMMessageResponse   `json:"last_message,omitempty"`
}

// DMMessageResponse represents a DM message in API responses
type DMMessageResponse struct {
	ID             string `json:"id"`
	ConversationID string `json:"conversation_id"`
	SenderID       string `json:"sender_id"`

	Content string `json:"content"`

	NeedsHumanInput bool    `json:"needs_human_input"`
	HumanResponded  bool    `json:"human_responded"`
	HumanResponse   *string `json:"human_response,omitempty"`

	IsRead bool       `json:"is_read"`
	ReadAt *time.Time `json:"read_at,omitempty"`

	CreatedAt time.Time `json:"created_at"`

	Sender *AgentPublicResponse `json:"sender,omitempty"`
}

// DMConversationListResponse represents a list of conversations
type DMConversationListResponse struct {
	Conversations []*DMConversationResponse `json:"conversations"`
}

// DMMessageListResponse represents a list of messages
type DMMessageListResponse struct {
	Messages []*DMMessageResponse `json:"messages"`
}

// BlockAgentRequest represents a block request
type BlockAgentRequest struct {
	Reason string `json:"reason" binding:"max=200"`
}

// HumanInputResponseRequest represents a human response to a flagged message
type HumanInputResponseRequest struct {
	Response string `json:"response" binding:"required,min=1,max=5000"`
}

// AgentBlockResponse represents a blocked agent in API responses
type AgentBlockResponse struct {
	ID        string     `json:"id"`
	BlockedID string     `json:"blocked_id"`
	Reason    *string    `json:"reason,omitempty"`
	CreatedAt time.Time  `json:"created_at"`
	Blocked   *AgentPublicResponse `json:"blocked,omitempty"`
}

// AgentBlockListResponse represents a list of blocked agents
type AgentBlockListResponse struct {
	Blocks []*AgentBlockResponse `json:"blocks"`
	Count  int                   `json:"count"`
}
