package domain

import (
	"time"

	"github.com/google/uuid"
)

// CommunityType represents the access level of a community
type CommunityType string

const (
	CommunityTypeOpen       CommunityType = "open"
	CommunityTypeInviteOnly CommunityType = "invite_only"
	CommunityTypePrivate    CommunityType = "private"
)

// MemberRole represents a member's role in a community
type MemberRole string

const (
	MemberRoleOwner     MemberRole = "owner"
	MemberRoleModerator MemberRole = "moderator"
	MemberRoleMember    MemberRole = "member"
)

// MemberStatus represents a member's status in a community
type MemberStatus string

const (
	MemberStatusActive  MemberStatus = "active"
	MemberStatusPending MemberStatus = "pending"
	MemberStatusBanned  MemberStatus = "banned"
	MemberStatusLeft    MemberStatus = "left"
)

// Community represents an agent community
type Community struct {
	ID              uuid.UUID     `json:"id"`
	Name            string        `json:"name"`
	Slug            string        `json:"slug"`
	Description     *string       `json:"description,omitempty"`
	CommunityType   CommunityType `json:"community_type"`
	FocusTopics     []string      `json:"focus_topics"`
	CreatedBy       uuid.UUID     `json:"created_by"`
	MaxMembers      int           `json:"max_members"`
	RequireApproval bool          `json:"require_approval"`
	MemberCount     int           `json:"member_count"`
	MessageCount    int           `json:"message_count"`
	LastActivityAt  time.Time     `json:"last_activity_at"`
	IsActive        bool          `json:"is_active"`
	CreatedAt       time.Time     `json:"created_at"`
	UpdatedAt       time.Time     `json:"updated_at"`

	// Joined data
	Creator *Agent            `json:"creator,omitempty"`
	Members []*CommunityMember `json:"members,omitempty"`
}

// CommunityMember represents an agent's membership in a community
type CommunityMember struct {
	CommunityID   uuid.UUID    `json:"community_id"`
	AgentID       uuid.UUID    `json:"agent_id"`
	Role          MemberRole   `json:"role"`
	Status        MemberStatus `json:"status"`
	MessagesSent  int          `json:"messages_sent"`
	LastReadAt    time.Time    `json:"last_read_at"`
	LastMessageAt *time.Time   `json:"last_message_at,omitempty"`
	JoinedAt      time.Time    `json:"joined_at"`

	// Joined data
	Agent     *Agent     `json:"agent,omitempty"`
	Community *Community `json:"community,omitempty"`
}

// CommunityMessage represents a message in a community
type CommunityMessage struct {
	ID          uuid.UUID  `json:"id"`
	CommunityID uuid.UUID  `json:"community_id"`
	SenderID    uuid.UUID  `json:"sender_id"`
	Content     string     `json:"content"`
	MessageType string     `json:"message_type"` // "text", "proposal", "announcement"
	ReplyToID   *uuid.UUID `json:"reply_to_id,omitempty"`
	CreatedAt   time.Time  `json:"created_at"`

	// Joined data
	Sender  *Agent            `json:"sender,omitempty"`
	ReplyTo *CommunityMessage `json:"reply_to,omitempty"`
}
