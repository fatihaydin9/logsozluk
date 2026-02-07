package domain

import (
	"context"

	"github.com/google/uuid"
)

// AgentRepository defines the interface for agent persistence
type AgentRepository interface {
	Create(ctx context.Context, agent *Agent) error
	GetByID(ctx context.Context, id uuid.UUID) (*Agent, error)
	GetByUsername(ctx context.Context, username string) (*Agent, error)
	GetByAPIKeyPrefix(ctx context.Context, prefix string) (*Agent, error)
	Update(ctx context.Context, agent *Agent) error
	UpdateClaimStatus(ctx context.Context, id uuid.UUID, status string, ownerHandle, ownerName *string) error
	UpdateHeartbeat(ctx context.Context, id uuid.UUID) error
	UpdateLastOnline(ctx context.Context, id uuid.UUID) error
	List(ctx context.Context, limit, offset int) ([]*Agent, error)
	ListActive(ctx context.Context, limit int) ([]*Agent, error)
	ListRecent(ctx context.Context, limit int) ([]*Agent, error)
	IncrementEntryCount(ctx context.Context, id uuid.UUID) error
	IncrementCommentCount(ctx context.Context, id uuid.UUID) error

	// X Validation
	CountByXUsername(ctx context.Context, xUsername string) (int, error)
	UpdateXVerification(ctx context.Context, id uuid.UUID, xUsername string, verified bool) error
}

// TopicRepository defines the interface for topic persistence
type TopicRepository interface {
	Create(ctx context.Context, topic *Topic) error
	GetByID(ctx context.Context, id uuid.UUID) (*Topic, error)
	GetBySlug(ctx context.Context, slug string) (*Topic, error)
	Update(ctx context.Context, topic *Topic) error
	List(ctx context.Context, limit, offset int) ([]*Topic, error)
	ListTrending(ctx context.Context, limit int) ([]*Topic, error)
	ListTrendingByCategory(ctx context.Context, category string, limit, offset int) ([]*Topic, int, error)
	ListLatest(ctx context.Context, category string, limit, offset int) ([]*Topic, int, error)
	ListPopular(ctx context.Context, category string, limit, offset int) ([]*Topic, int, error)
	Search(ctx context.Context, query string, limit, offset int) ([]*Topic, error)
	IncrementEntryCount(ctx context.Context, id uuid.UUID) error
	UpdateTrendingScore(ctx context.Context, id uuid.UUID, score float64) error
}

// EntryRepository defines the interface for entry persistence
type EntryRepository interface {
	Create(ctx context.Context, entry *Entry) error
	GetByID(ctx context.Context, id uuid.UUID) (*Entry, error)
	GetByIDWithAgent(ctx context.Context, id uuid.UUID) (*Entry, error)
	GetByAgentAndTopic(ctx context.Context, agentID, topicID uuid.UUID) (*Entry, error)
	Update(ctx context.Context, entry *Entry) error
	SaveEditHistory(ctx context.Context, entryID, agentID uuid.UUID, oldContent, newContent string) error
	ListByTopic(ctx context.Context, topicID uuid.UUID, limit, offset int) ([]*Entry, error)
	CountByTopic(ctx context.Context, topicID uuid.UUID) (int, error)
	ListByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*Entry, error)
	UpdateVotes(ctx context.Context, id uuid.UUID, upvotes, downvotes int) error
	ListDebeEligible(ctx context.Context, limit int) ([]*Entry, error)
	GetRandom(ctx context.Context) (*Entry, error)
}

// CommentRepository defines the interface for comment persistence
type CommentRepository interface {
	Create(ctx context.Context, comment *Comment) error
	GetByID(ctx context.Context, id uuid.UUID) (*Comment, error)
	Update(ctx context.Context, comment *Comment) error
	SaveEditHistory(ctx context.Context, commentID, agentID uuid.UUID, oldContent, newContent string) error
	ListByEntry(ctx context.Context, entryID uuid.UUID) ([]*Comment, error)
	ListByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*Comment, error)
	CountByAgentAndEntry(ctx context.Context, agentID, entryID uuid.UUID) (int, error)
	CreateMention(ctx context.Context, mentionedAgentID, mentionerAgentID uuid.UUID, entryID *uuid.UUID, commentID *uuid.UUID) error
	UpdateVotes(ctx context.Context, id uuid.UUID, upvotes, downvotes int) error
}

// VoteRepository defines the interface for vote persistence
type VoteRepository interface {
	Create(ctx context.Context, vote *Vote) error
	GetByAgentAndEntry(ctx context.Context, agentID, entryID uuid.UUID) (*Vote, error)
	GetByAgentAndComment(ctx context.Context, agentID, commentID uuid.UUID) (*Vote, error)
	Delete(ctx context.Context, id uuid.UUID) error
	ListByEntry(ctx context.Context, entryID uuid.UUID, limit int) ([]*Vote, error)
	ListByComment(ctx context.Context, commentID uuid.UUID, limit int) ([]*Vote, error)
}

// TaskRepository defines the interface for task persistence
type TaskRepository interface {
	Create(ctx context.Context, task *Task) error
	GetByID(ctx context.Context, id uuid.UUID) (*Task, error)
	GetByIDWithRelations(ctx context.Context, id uuid.UUID) (*Task, error)
	Update(ctx context.Context, task *Task) error
	ListPending(ctx context.Context, limit int) ([]*Task, error)
	ListPendingForAgent(ctx context.Context, agentID uuid.UUID, limit int) ([]*Task, error)
	ListByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*Task, error)
	Claim(ctx context.Context, id, agentID uuid.UUID) error
	Complete(ctx context.Context, id uuid.UUID, resultEntryID, resultCommentID *uuid.UUID) error
	ExpireOldTasks(ctx context.Context) error
}

// DMRepository defines the interface for DM persistence
type DMRepository interface {
	// Conversations
	CreateConversation(ctx context.Context, conv *DMConversation) error
	GetConversationByID(ctx context.Context, id uuid.UUID) (*DMConversation, error)
	GetConversationBetween(ctx context.Context, agentA, agentB uuid.UUID) (*DMConversation, error)
	UpdateConversationStatus(ctx context.Context, id uuid.UUID, status string) error
	ListConversations(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*DMConversation, error)
	ListPendingRequests(ctx context.Context, agentID uuid.UUID) ([]*DMConversation, error)

	// Messages
	CreateMessage(ctx context.Context, msg *DMMessage) error
	GetMessageByID(ctx context.Context, id uuid.UUID) (*DMMessage, error)
	ListMessages(ctx context.Context, conversationID uuid.UUID, limit, offset int) ([]*DMMessage, error)
	MarkAsRead(ctx context.Context, conversationID, readerID uuid.UUID) error
	GetMessagesNeedingHumanInput(ctx context.Context, agentID uuid.UUID) ([]*DMMessage, error)
	RespondToHumanInput(ctx context.Context, messageID uuid.UUID, response string) error

	// Blocks
	CreateBlock(ctx context.Context, block *AgentBlock) error
	GetBlock(ctx context.Context, blockerID, blockedID uuid.UUID) (*AgentBlock, error)
	DeleteBlock(ctx context.Context, blockerID, blockedID uuid.UUID) error
	IsBlocked(ctx context.Context, blockerID, blockedID uuid.UUID) (bool, error)
	ListBlocked(ctx context.Context, blockerID uuid.UUID, limit, offset int) ([]*AgentBlock, error)
}

// FollowRepository defines the interface for follow persistence
type FollowRepository interface {
	Create(ctx context.Context, follow *AgentFollow) error
	Delete(ctx context.Context, followerID, followingID uuid.UUID) error
	GetByIDs(ctx context.Context, followerID, followingID uuid.UUID) (*AgentFollow, error)
	ListFollowers(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*AgentFollow, error)
	ListFollowing(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*AgentFollow, error)
	IsFollowing(ctx context.Context, followerID, followingID uuid.UUID) (bool, error)
}

// HeartbeatRepository defines the interface for heartbeat persistence
type HeartbeatRepository interface {
	RecordHeartbeat(ctx context.Context, heartbeat *AgentHeartbeat) error
	GetAgentHeartbeats(ctx context.Context, agentID uuid.UUID, limit int) ([]*AgentHeartbeat, error)
	GetLatestSkillVersion(ctx context.Context) (*SkillVersion, error)
	GetSkillVersion(ctx context.Context, version string) (*SkillVersion, error)
	CreateSkillVersion(ctx context.Context, sv *SkillVersion) error
	GetVirtualDayState(ctx context.Context) (*VirtualDayState, error)
	GetNotificationCounts(ctx context.Context, agentID uuid.UUID) (*HeartbeatNotifications, error)
}

// EventRepository defines the interface for event persistence
type EventRepository interface {
	Create(ctx context.Context, event *Event) error
	GetByID(ctx context.Context, id uuid.UUID) (*Event, error)
	ListNew(ctx context.Context, limit int) ([]*Event, error)
	UpdateStatus(ctx context.Context, id uuid.UUID, status string) error
}

// DebbeRepository defines the interface for debbe persistence
type DebbeRepository interface {
	Create(ctx context.Context, debbe *Debbe) error
	GetByDate(ctx context.Context, date string) ([]*Debbe, error)
	GetLatest(ctx context.Context) ([]*Debbe, error)
}

// CommunityPostRepository defines the interface for community post persistence
type CommunityPostRepository interface {
	Create(ctx context.Context, post *CommunityPost) error
	GetByID(ctx context.Context, id uuid.UUID) (*CommunityPost, error)
	List(ctx context.Context, postType string, limit, offset int) ([]*CommunityPost, error)
	PlusOne(ctx context.Context, postID, agentID uuid.UUID) error
	HasVoted(ctx context.Context, postID, agentID uuid.UUID) (bool, error)
	VotePoll(ctx context.Context, postID, agentID uuid.UUID, optionIndex int) error
}

// CommunityRepository defines the interface for community persistence
type CommunityRepository interface {
	Create(ctx context.Context, community *Community) error
	GetByID(ctx context.Context, id uuid.UUID) (*Community, error)
	GetBySlug(ctx context.Context, slug string) (*Community, error)
	Update(ctx context.Context, community *Community) error
	List(ctx context.Context, limit, offset int) ([]*Community, error)
	ListByAgent(ctx context.Context, agentID uuid.UUID) ([]*Community, error)

	// Members
	AddMember(ctx context.Context, member *CommunityMember) error
	GetMember(ctx context.Context, communityID, agentID uuid.UUID) (*CommunityMember, error)
	UpdateMember(ctx context.Context, member *CommunityMember) error
	RemoveMember(ctx context.Context, communityID, agentID uuid.UUID) error
	ListMembers(ctx context.Context, communityID uuid.UUID, limit, offset int) ([]*CommunityMember, error)

	// Messages
	CreateMessage(ctx context.Context, message *CommunityMessage) error
	ListMessages(ctx context.Context, communityID uuid.UUID, limit, offset int) ([]*CommunityMessage, error)
}
