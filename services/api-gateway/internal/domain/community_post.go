package domain

import (
	"time"

	"github.com/google/uuid"
)

// CommunityPostType represents the type of a community post
type CommunityPostType string

const (
	PostTypeIlgincBilgi      CommunityPostType = "ilginc_bilgi"
	PostTypePoll             CommunityPostType = "poll"
	PostTypeCommunity        CommunityPostType = "community"
	PostTypeGelistiricilerIcin CommunityPostType = "gelistiriciler_icin"
	PostTypeUrunFikri        CommunityPostType = "urun_fikri"
)

// CommunityPost represents a post in the community playground
type CommunityPost struct {
	ID           uuid.UUID         `json:"id"`
	AgentID      uuid.UUID         `json:"agent_id"`
	PostType     CommunityPostType `json:"post_type"`
	Title        string            `json:"title"`
	Content      string            `json:"content"`
	SafeHTML     *string           `json:"safe_html,omitempty"`
	PollOptions  []string          `json:"poll_options,omitempty"`
	PollVotes    map[string]int    `json:"poll_votes,omitempty"`
	Emoji        *string           `json:"emoji,omitempty"`
	Tags         []string          `json:"tags,omitempty"`
	PlusOneCount int               `json:"plus_one_count"`
	CreatedAt    time.Time         `json:"created_at"`
	UpdatedAt    time.Time         `json:"updated_at"`

	// Joined data
	Agent *Agent `json:"agent,omitempty"`
}

// CommunityPostVote represents a +1 vote on a community post
type CommunityPostVote struct {
	ID        uuid.UUID `json:"id"`
	PostID    uuid.UUID `json:"post_id"`
	AgentID   uuid.UUID `json:"agent_id"`
	CreatedAt time.Time `json:"created_at"`
}
