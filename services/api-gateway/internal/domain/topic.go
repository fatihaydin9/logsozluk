package domain

import (
	"time"

	"github.com/google/uuid"
)

// Topic represents a discussion topic (başlık)
type Topic struct {
	ID       uuid.UUID
	Slug     string
	Title    string
	Category string
	Tags     []string

	CreatedBy  *uuid.UUID
	EntryCount int

	TrendingScore float64
	LastEntryAt   *time.Time

	VirtualDayPhase *string
	PhaseEntryCount int

	IsLocked bool
	IsHidden bool

	CreatedAt time.Time
	UpdatedAt time.Time
}

// CanAcceptEntries returns true if new entries can be added
func (t *Topic) CanAcceptEntries() bool {
	return !t.IsLocked && !t.IsHidden
}
