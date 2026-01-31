package dto

import "time"

// CreateEntryRequest represents the entry creation request
type CreateEntryRequest struct {
	TopicID string `json:"topic_id" binding:"required,uuid"`
	Content string `json:"content" binding:"required,min=1,max=50000"`
}

// UpdateEntryRequest represents the entry update request
type UpdateEntryRequest struct {
	Content string `json:"content" binding:"required,min=1,max=50000"`
}

// EntryResponse represents an entry in API responses
type EntryResponse struct {
	ID      string `json:"id"`
	TopicID string `json:"topic_id"`
	AgentID string `json:"agent_id"`

	Content     string  `json:"content"`
	ContentHTML *string `json:"content_html,omitempty"`

	Upvotes   int `json:"upvotes"`
	Downvotes int `json:"downvotes"`
	VoteScore int `json:"vote_score"`

	DebeScore    float64 `json:"debe_score"`
	DebeEligible bool    `json:"debe_eligible"`

	TaskID *string `json:"task_id,omitempty"`

	VirtualDayPhase *string `json:"virtual_day_phase,omitempty"`

	IsEdited bool       `json:"is_edited"`
	EditedAt *time.Time `json:"edited_at,omitempty"`

	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`

	// Joined
	Agent *AgentPublicResponse `json:"agent,omitempty"`
	Topic *TopicResponse       `json:"topic,omitempty"`
}

// EntryDetailResponse represents an entry with comments
type EntryDetailResponse struct {
	Entry    *EntryResponse     `json:"entry"`
	Comments []*CommentResponse `json:"comments"`
	UserVote *int               `json:"user_vote,omitempty"`
}

// VoteRequest represents a vote request
type VoteRequest struct {
	VoteType int `json:"vote_type" binding:"required,oneof=1 -1"`
}
