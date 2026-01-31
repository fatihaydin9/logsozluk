package domain

import "fmt"

// ErrorCategory represents the type of domain error
type ErrorCategory string

const (
	ErrCategoryValidation   ErrorCategory = "validation"
	ErrCategoryNotFound     ErrorCategory = "not_found"
	ErrCategoryConflict     ErrorCategory = "conflict"
	ErrCategoryUnauthorized ErrorCategory = "unauthorized"
	ErrCategoryForbidden    ErrorCategory = "forbidden"
	ErrCategoryInternal     ErrorCategory = "internal"
)

// Error represents a domain-level error with context
type Error struct {
	Category ErrorCategory
	Code     string
	Message  string
	Field    string // Optional: for validation errors
	Cause    error  // Optional: underlying error
}

func (e *Error) Error() string {
	if e.Field != "" {
		return fmt.Sprintf("[%s] %s: %s (field: %s)", e.Category, e.Code, e.Message, e.Field)
	}
	return fmt.Sprintf("[%s] %s: %s", e.Category, e.Code, e.Message)
}

func (e *Error) Unwrap() error {
	return e.Cause
}

// Error constructors

func NewValidationError(code, message, field string) *Error {
	return &Error{
		Category: ErrCategoryValidation,
		Code:     code,
		Message:  message,
		Field:    field,
	}
}

func NewNotFoundError(code, message string) *Error {
	return &Error{
		Category: ErrCategoryNotFound,
		Code:     code,
		Message:  message,
	}
}

func NewConflictError(code, message string) *Error {
	return &Error{
		Category: ErrCategoryConflict,
		Code:     code,
		Message:  message,
	}
}

func NewUnauthorizedError(code, message string) *Error {
	return &Error{
		Category: ErrCategoryUnauthorized,
		Code:     code,
		Message:  message,
	}
}

func NewForbiddenError(code, message string) *Error {
	return &Error{
		Category: ErrCategoryForbidden,
		Code:     code,
		Message:  message,
	}
}

func NewInternalError(code, message string, cause error) *Error {
	return &Error{
		Category: ErrCategoryInternal,
		Code:     code,
		Message:  message,
		Cause:    cause,
	}
}

// Common domain errors

var (
	// Agent errors
	ErrAgentNotFound      = NewNotFoundError("agent_not_found", "Agent not found")
	ErrAgentAlreadyExists = NewConflictError("agent_exists", "Agent with this username already exists")
	ErrAgentBanned        = NewForbiddenError("agent_banned", "Agent is banned")
	ErrAgentNotClaimed    = NewForbiddenError("agent_not_claimed", "Agent must be claimed to perform this action")
	ErrInvalidAPIKey      = NewUnauthorizedError("invalid_api_key", "Invalid or missing API key")

	// Topic errors
	ErrTopicNotFound      = NewNotFoundError("topic_not_found", "Topic not found")
	ErrTopicAlreadyExists = NewConflictError("topic_exists", "Topic with this slug already exists")
	ErrTopicLocked        = NewForbiddenError("topic_locked", "Topic is locked")

	// Entry errors
	ErrEntryNotFound = NewNotFoundError("entry_not_found", "Entry not found")
	ErrEntryHidden   = NewForbiddenError("entry_hidden", "Entry is hidden")

	// Comment errors
	ErrCommentNotFound = NewNotFoundError("comment_not_found", "Comment not found")
	ErrMaxDepthReached = NewValidationError("max_depth", "Maximum comment depth reached", "parent_comment_id")

	// Task errors
	ErrTaskNotFound      = NewNotFoundError("task_not_found", "Task not found")
	ErrTaskAlreadyClaimed = NewConflictError("task_claimed", "Task is already claimed")
	ErrTaskExpired       = NewConflictError("task_expired", "Task has expired")
	ErrTaskNotAssigned   = NewForbiddenError("task_not_assigned", "Task is not assigned to you")

	// Vote errors
	ErrAlreadyVoted   = NewConflictError("already_voted", "You have already voted on this item")
	ErrCannotVoteOwn  = NewForbiddenError("cannot_vote_own", "You cannot vote on your own content")

	// DM errors
	ErrConversationNotFound = NewNotFoundError("conversation_not_found", "Conversation not found")
	ErrConversationExists   = NewConflictError("conversation_exists", "Conversation already exists")
	ErrConversationPending  = NewForbiddenError("conversation_pending", "Conversation request is pending")
	ErrConversationRejected = NewForbiddenError("conversation_rejected", "Conversation request was rejected")
	ErrAgentBlocked         = NewForbiddenError("agent_blocked", "You are blocked by this agent")
	ErrMessageNotFound      = NewNotFoundError("message_not_found", "Message not found")

	// Rate limit errors
	ErrRateLimitExceeded = NewForbiddenError("rate_limit", "Rate limit exceeded")

	// Follow errors
	ErrAlreadyFollowing = NewConflictError("already_following", "You are already following this agent")
	ErrNotFollowing     = NewNotFoundError("not_following", "You are not following this agent")
	ErrCannotFollowSelf = NewValidationError("cannot_follow_self", "You cannot follow yourself", "following_id")
)

// IsCategory checks if the error belongs to a specific category
func IsCategory(err error, category ErrorCategory) bool {
	if domainErr, ok := err.(*Error); ok {
		return domainErr.Category == category
	}
	return false
}

func IsNotFound(err error) bool {
	return IsCategory(err, ErrCategoryNotFound)
}

func IsValidation(err error) bool {
	return IsCategory(err, ErrCategoryValidation)
}

func IsConflict(err error) bool {
	return IsCategory(err, ErrCategoryConflict)
}

func IsUnauthorized(err error) bool {
	return IsCategory(err, ErrCategoryUnauthorized)
}

func IsForbidden(err error) bool {
	return IsCategory(err, ErrCategoryForbidden)
}
