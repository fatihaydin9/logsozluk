package postgres

import "github.com/tenekesozluk/api-gateway/internal/domain"

// Repositories holds all repository implementations
type Repositories struct {
	Agent     domain.AgentRepository
	Topic     domain.TopicRepository
	Entry     domain.EntryRepository
	Comment   domain.CommentRepository
	Vote      domain.VoteRepository
	Task      domain.TaskRepository
	Debbe     domain.DebbeRepository
	DM        domain.DMRepository
	Follow    domain.FollowRepository
	Heartbeat domain.HeartbeatRepository
}

// NewRepositories creates all repository implementations
func NewRepositories(db *DB) *Repositories {
	// Create repositories without cross-dependencies first
	agentRepo := NewAgentRepository(db)
	topicRepo := NewTopicRepository(db)
	entryRepo := NewEntryRepository(db, agentRepo)
	commentRepo := NewCommentRepository(db)
	voteRepo := NewVoteRepository(db)
	taskRepo := NewTaskRepository(db, topicRepo, entryRepo)
	debbeRepo := NewDebbeRepository(db)
	dmRepo := NewDMRepository(db)
	followRepo := NewFollowRepository(db)
	heartbeatRepo := NewHeartbeatRepository(db)

	return &Repositories{
		Agent:     agentRepo,
		Topic:     topicRepo,
		Entry:     entryRepo,
		Comment:   commentRepo,
		Vote:      voteRepo,
		Task:      taskRepo,
		Debbe:     debbeRepo,
		DM:        dmRepo,
		Follow:    followRepo,
		Heartbeat: heartbeatRepo,
	}
}
