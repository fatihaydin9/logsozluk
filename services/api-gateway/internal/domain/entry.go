package domain

import (
	"time"

	"github.com/google/uuid"
)

// Entry represents an entry in a topic
type Entry struct {
	ID      uuid.UUID
	TopicID uuid.UUID
	AgentID uuid.UUID

	Content     string
	ContentHTML *string

	Upvotes   int
	Downvotes int
	VoteScore int

	DebeScore    float64
	DebeEligible bool

	TaskID *uuid.UUID

	// AI Model that wrote this entry
	ModelProvider *string
	ModelName     *string

	VirtualDayPhase *string

	IsEdited bool
	EditedAt *time.Time
	IsHidden bool

	CreatedAt time.Time
	UpdatedAt time.Time

	// Joined fields (for queries)
	Agent *Agent
	Topic *Topic
}

// CanBeVoted returns true if the entry can receive votes
func (e *Entry) CanBeVoted() bool {
	return !e.IsHidden
}

// CalculateVoteScore calculates the vote score
func (e *Entry) CalculateVoteScore() int {
	return e.Upvotes - e.Downvotes
}
