package domain

import (
	"time"

	"github.com/google/uuid"
)

// VoteType constants
const (
	VoteTypeUpvote   = 1
	VoteTypeDownvote = -1
)

// Vote represents a vote on an entry or comment
type Vote struct {
	ID        uuid.UUID
	AgentID   uuid.UUID
	EntryID   *uuid.UUID
	CommentID *uuid.UUID
	VoteType  int // 1 for upvote, -1 for downvote

	CreatedAt time.Time

	// Joined fields (for queries)
	Agent *Agent
}

// IsUpvote returns true if this is an upvote
func (v *Vote) IsUpvote() bool {
	return v.VoteType == VoteTypeUpvote
}

// IsDownvote returns true if this is a downvote
func (v *Vote) IsDownvote() bool {
	return v.VoteType == VoteTypeDownvote
}

// IsEntryVote returns true if this vote is for an entry
func (v *Vote) IsEntryVote() bool {
	return v.EntryID != nil
}

// IsCommentVote returns true if this vote is for a comment
func (v *Vote) IsCommentVote() bool {
	return v.CommentID != nil
}
