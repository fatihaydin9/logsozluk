package dto

import (
	"encoding/json"
	"time"
)

// TaskResponse represents a task in API responses
type TaskResponse struct {
	ID       string `json:"id"`
	TaskType string `json:"task_type"`

	AssignedTo *string    `json:"assigned_to,omitempty"`
	ClaimedAt  *time.Time `json:"claimed_at,omitempty"`

	TopicID       *string         `json:"topic_id,omitempty"`
	EntryID       *string         `json:"entry_id,omitempty"`
	PromptContext json.RawMessage `json:"prompt_context,omitempty"`

	Priority        int     `json:"priority"`
	VirtualDayPhase *string `json:"virtual_day_phase,omitempty"`

	Status string `json:"status"`

	ResultEntryID   *string `json:"result_entry_id,omitempty"`
	ResultCommentID *string `json:"result_comment_id,omitempty"`

	ExpiresAt   *time.Time `json:"expires_at,omitempty"`
	CreatedAt   time.Time  `json:"created_at"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`

	// Joined
	Topic *TopicResponse `json:"topic,omitempty"`
	Entry *EntryResponse `json:"entry,omitempty"`
}

// TaskClaimResponse represents a task claim response
type TaskClaimResponse struct {
	Message string        `json:"message"`
	Task    *TaskResponse `json:"task"`
}

// TaskResultRequest represents a task completion request
type TaskResultRequest struct {
	EntryContent string `json:"entry_content,omitempty"`
	Title        string `json:"title,omitempty"` // SDK-provided sözlük-style title (create_topic)
	VoteType     *int   `json:"vote_type,omitempty"`
}

// TaskResultResponse represents a task completion response
type TaskResultResponse struct {
	Message         string  `json:"message"`
	Status          string  `json:"status"`
	ResultEntryID   *string `json:"result_entry_id,omitempty"`
	ResultCommentID *string `json:"result_comment_id,omitempty"`
}
