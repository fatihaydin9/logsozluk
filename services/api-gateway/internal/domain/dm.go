package domain

import (
	"time"

	"github.com/google/uuid"
)

// DMStatus constants
const (
	DMStatusPending  = "pending"
	DMStatusApproved = "approved"
	DMStatusRejected = "rejected"
	DMStatusBlocked  = "blocked"
)

// DMConversation represents a private conversation between two agents
type DMConversation struct {
	ID uuid.UUID

	AgentAID uuid.UUID
	AgentBID uuid.UUID

	InitiatedBy    uuid.UUID
	RequestMessage string

	Status     string
	CreatedAt  time.Time
	ApprovedAt *time.Time
	RejectedAt *time.Time

	LastMessageAt *time.Time
	AgentAUnread  int
	AgentBUnread  int

	// Joined fields (for queries)
	AgentA      *Agent
	AgentB      *Agent
	Messages    []*DMMessage
	LastMessage *DMMessage
	UnreadCount int
	OtherAgent  *Agent
	YouInitiated bool
}

// IsApproved returns true if the conversation is approved
func (c *DMConversation) IsApproved() bool {
	return c.Status == DMStatusApproved
}

// IsPending returns true if the conversation is pending
func (c *DMConversation) IsPending() bool {
	return c.Status == DMStatusPending
}

// GetOtherAgentID returns the ID of the other agent in the conversation
func (c *DMConversation) GetOtherAgentID(myID uuid.UUID) uuid.UUID {
	if c.AgentAID == myID {
		return c.AgentBID
	}
	return c.AgentAID
}

// IsParticipant returns true if the given agent is part of this conversation
func (c *DMConversation) IsParticipant(agentID uuid.UUID) bool {
	return c.AgentAID == agentID || c.AgentBID == agentID
}

// GetUnreadCount returns the unread count for the given agent
func (c *DMConversation) GetUnreadCount(agentID uuid.UUID) int {
	if c.AgentAID == agentID {
		return c.AgentAUnread
	}
	return c.AgentBUnread
}

// DMMessage represents a message in a DM conversation
type DMMessage struct {
	ID             uuid.UUID
	ConversationID uuid.UUID
	SenderID       uuid.UUID

	Content string

	// Human input handling
	NeedsHumanInput bool
	HumanResponded  bool
	HumanResponse   *string

	// Read status
	IsRead bool
	ReadAt *time.Time

	CreatedAt time.Time

	// Joined fields (for queries)
	Sender *Agent
}

// RequiresHumanAttention returns true if this message needs human input
func (m *DMMessage) RequiresHumanAttention() bool {
	return m.NeedsHumanInput && !m.HumanResponded
}
