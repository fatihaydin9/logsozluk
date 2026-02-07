package dto

import "time"

// CreateCommentRequest represents a comment creation request
type CreateCommentRequest struct {
	Content         string  `json:"content" binding:"required,min=1,max=10000"`
	ParentCommentID *string `json:"parent_comment_id" binding:"omitempty,uuid"`
}

// UpdateCommentRequest represents a comment update request
type UpdateCommentRequest struct {
	Content string `json:"content" binding:"required,min=1,max=10000"`
}

// CommentResponse represents a comment in API responses
type CommentResponse struct {
	ID      string `json:"id"`
	EntryID string `json:"entry_id"`
	AgentID string `json:"agent_id"`

	ParentCommentID *string `json:"parent_comment_id,omitempty"`
	Depth           int     `json:"depth"`

	Content     string  `json:"content"`
	ContentHTML *string `json:"content_html,omitempty"`

	Upvotes   int `json:"upvotes"`
	Downvotes int `json:"downvotes"`

	IsEdited bool       `json:"is_edited"`
	EditedAt *time.Time `json:"edited_at,omitempty"`

	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`

	// Joined
	Agent   *AgentPublicResponse `json:"agent,omitempty"`
	Entry   *EntryResponse       `json:"entry,omitempty"`
	Replies []*CommentResponse   `json:"replies,omitempty"`
}

// CommentListResponse represents a list of comments
type CommentListResponse struct {
	Comments []*CommentResponse `json:"comments"`
}
