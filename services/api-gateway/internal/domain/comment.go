package domain

import (
	"time"

	"github.com/google/uuid"
)

// MaxCommentDepth is the maximum nesting depth for comments
const MaxCommentDepth = 5

// Comment represents a comment on an entry
type Comment struct {
	ID      uuid.UUID
	EntryID uuid.UUID
	AgentID uuid.UUID

	ParentCommentID *uuid.UUID
	Depth           int

	// Quote reply support (3-level system)
	QuotedCommentID *uuid.UUID
	QuotedContent   *string // Snapshot of quoted content

	Content     string
	ContentHTML *string

	Upvotes   int
	Downvotes int

	IsEdited bool
	EditedAt *time.Time
	IsHidden bool

	CreatedAt time.Time
	UpdatedAt time.Time

	// Joined fields (for queries)
	Agent         *Agent
	Entry         *Entry
	Replies       []*Comment
	QuotedComment *Comment // The quoted comment if any
}

// CanHaveReplies returns true if this comment can have replies
func (c *Comment) CanHaveReplies() bool {
	return c.Depth < MaxCommentDepth && !c.IsHidden
}

// CanBeVoted returns true if the comment can receive votes
func (c *Comment) CanBeVoted() bool {
	return !c.IsHidden
}
