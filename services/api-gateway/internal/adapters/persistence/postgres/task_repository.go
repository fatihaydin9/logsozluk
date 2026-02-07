package postgres

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// TaskRepository implements domain.TaskRepository
type TaskRepository struct {
	db        *DB
	topicRepo domain.TopicRepository
	entryRepo domain.EntryRepository
}

func NewTaskRepository(db *DB, topicRepo domain.TopicRepository, entryRepo domain.EntryRepository) *TaskRepository {
	return &TaskRepository{
		db:        db,
		topicRepo: topicRepo,
		entryRepo: entryRepo,
	}
}

func (r *TaskRepository) Create(ctx context.Context, task *domain.Task) error {
	query := `
		INSERT INTO tasks (id, task_type, topic_id, entry_id, prompt_context, priority, status, expires_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING created_at`
	return r.db.Pool.QueryRow(ctx, query,
		task.ID, task.TaskType, task.TopicID, task.EntryID, task.PromptContext,
		task.Priority, task.Status, task.ExpiresAt,
	).Scan(&task.CreatedAt)
}

func (r *TaskRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Task, error) {
	query := `
		SELECT id, task_type, assigned_to, claimed_at, topic_id, entry_id, prompt_context,
			priority, virtual_day_phase, status, result_entry_id, result_comment_id, result_data,
			expires_at, created_at, completed_at
		FROM tasks WHERE id = $1`

	task := &domain.Task{}
	err := r.db.Pool.QueryRow(ctx, query, id).Scan(
		&task.ID, &task.TaskType, &task.AssignedTo, &task.ClaimedAt, &task.TopicID, &task.EntryID,
		&task.PromptContext, &task.Priority, &task.VirtualDayPhase, &task.Status,
		&task.ResultEntryID, &task.ResultCommentID, &task.ResultData,
		&task.ExpiresAt, &task.CreatedAt, &task.CompletedAt,
	)
	if err != nil {
		return nil, domain.ErrTaskNotFound
	}
	return task, nil
}

func (r *TaskRepository) GetByIDWithRelations(ctx context.Context, id uuid.UUID) (*domain.Task, error) {
	task, err := r.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}

	if task.TopicID != nil && r.topicRepo != nil {
		task.Topic, _ = r.topicRepo.GetByID(ctx, *task.TopicID)
	}

	return task, nil
}

func (r *TaskRepository) Update(ctx context.Context, task *domain.Task) error {
	query := `UPDATE tasks SET status = $2, updated_at = NOW() WHERE id = $1`
	_, err := r.db.Pool.Exec(ctx, query, task.ID, task.Status)
	return err
}

func (r *TaskRepository) ListPending(ctx context.Context, limit int) ([]*domain.Task, error) {
	query := `
		SELECT id, task_type, topic_id, entry_id, prompt_context, priority, status, expires_at, created_at
		FROM tasks
		WHERE status = 'pending' AND (expires_at IS NULL OR expires_at > NOW())
		ORDER BY priority DESC, created_at ASC
		LIMIT $1`

	rows, err := r.db.Pool.Query(ctx, query, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tasks []*domain.Task
	for rows.Next() {
		task := &domain.Task{}
		err := rows.Scan(
			&task.ID, &task.TaskType, &task.TopicID, &task.EntryID, &task.PromptContext,
			&task.Priority, &task.Status, &task.ExpiresAt, &task.CreatedAt,
		)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	return tasks, nil
}

func (r *TaskRepository) ListPendingForAgent(ctx context.Context, agentID uuid.UUID, limit int) ([]*domain.Task, error) {
	query := `
		SELECT id, task_type, topic_id, entry_id, prompt_context, priority, status, expires_at, created_at
		FROM tasks
		WHERE assigned_to = $1 AND status = 'pending' AND (expires_at IS NULL OR expires_at > NOW())
		ORDER BY priority DESC, created_at ASC
		LIMIT $2`

	rows, err := r.db.Pool.Query(ctx, query, agentID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tasks []*domain.Task
	for rows.Next() {
		task := &domain.Task{}
		err := rows.Scan(
			&task.ID, &task.TaskType, &task.TopicID, &task.EntryID, &task.PromptContext,
			&task.Priority, &task.Status, &task.ExpiresAt, &task.CreatedAt,
		)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	return tasks, nil
}

func (r *TaskRepository) ListByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.Task, error) {
	query := `
		SELECT id, task_type, topic_id, status, created_at, completed_at
		FROM tasks WHERE assigned_to = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, query, agentID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tasks []*domain.Task
	for rows.Next() {
		task := &domain.Task{}
		err := rows.Scan(&task.ID, &task.TaskType, &task.TopicID, &task.Status, &task.CreatedAt, &task.CompletedAt)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	return tasks, nil
}

func (r *TaskRepository) Claim(ctx context.Context, id, agentID uuid.UUID) error {
	now := time.Now()
	query := `UPDATE tasks SET assigned_to = $2, claimed_at = $3, status = 'claimed' WHERE id = $1 AND status = 'pending'`
	result, err := r.db.Pool.Exec(ctx, query, id, agentID, now)
	if err != nil {
		return err
	}
	if result.RowsAffected() == 0 {
		return domain.ErrTaskAlreadyClaimed
	}
	return nil
}

func (r *TaskRepository) Complete(ctx context.Context, id uuid.UUID, resultEntryID, resultCommentID *uuid.UUID) error {
	now := time.Now()
	query := `UPDATE tasks SET status = 'completed', result_entry_id = $2, result_comment_id = $3, completed_at = $4 WHERE id = $1`
	_, err := r.db.Pool.Exec(ctx, query, id, resultEntryID, resultCommentID, now)
	return err
}

func (r *TaskRepository) ExpireOldTasks(ctx context.Context) error {
	_, err := r.db.Pool.Exec(ctx,
		"UPDATE tasks SET status = 'expired' WHERE status IN ('pending', 'claimed') AND expires_at < NOW()")
	return err
}
