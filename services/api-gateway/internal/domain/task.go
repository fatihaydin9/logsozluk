package domain

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

// TaskType constants
const (
	TaskTypeWriteEntry   = "write_entry"
	TaskTypeWriteComment = "write_comment"
	TaskTypeCreateTopic  = "create_topic"
	TaskTypeVote           = "vote"
	TaskTypeCommunityPost  = "community_post"
)

// TaskStatus constants
const (
	TaskStatusPending   = "pending"
	TaskStatusClaimed   = "claimed"
	TaskStatusCompleted = "completed"
	TaskStatusFailed    = "failed"
	TaskStatusExpired   = "expired"
)

// Task represents a task for agents
type Task struct {
	ID       uuid.UUID
	TaskType string

	AssignedTo *uuid.UUID
	ClaimedAt  *time.Time

	TopicID       *uuid.UUID
	EntryID       *uuid.UUID
	PromptContext json.RawMessage

	Priority        int
	VirtualDayPhase *string

	Status string

	ResultEntryID   *uuid.UUID
	ResultCommentID *uuid.UUID
	ResultData      json.RawMessage

	ExpiresAt   *time.Time
	CreatedAt   time.Time
	CompletedAt *time.Time

	// Joined fields (for queries)
	Topic *Topic
	Entry *Entry
}

// IsPending returns true if the task is pending
func (t *Task) IsPending() bool {
	return t.Status == TaskStatusPending
}

// IsClaimed returns true if the task is claimed
func (t *Task) IsClaimed() bool {
	return t.Status == TaskStatusClaimed
}

// IsCompleted returns true if the task is completed
func (t *Task) IsCompleted() bool {
	return t.Status == TaskStatusCompleted
}

// IsExpired returns true if the task has expired
func (t *Task) IsExpired() bool {
	if t.ExpiresAt == nil {
		return false
	}
	return time.Now().After(*t.ExpiresAt)
}

// CanBeClaimed returns true if the task can be claimed
func (t *Task) CanBeClaimed() bool {
	return t.IsPending() && !t.IsExpired()
}

// IsAssignedTo returns true if the task is assigned to the given agent
func (t *Task) IsAssignedTo(agentID uuid.UUID) bool {
	return t.AssignedTo != nil && *t.AssignedTo == agentID
}
