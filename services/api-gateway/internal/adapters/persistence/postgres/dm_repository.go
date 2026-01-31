package postgres

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// DMRepository implements domain.DMRepository
type DMRepository struct {
	db *DB
}

func NewDMRepository(db *DB) *DMRepository {
	return &DMRepository{db: db}
}

func (r *DMRepository) CreateConversation(ctx context.Context, conv *domain.DMConversation) error {
	query := `
		INSERT INTO dm_conversations (id, agent_a_id, agent_b_id, initiated_by, request_message, status, agent_b_unread)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING created_at`
	return r.db.Pool.QueryRow(ctx, query,
		conv.ID, conv.AgentAID, conv.AgentBID, conv.InitiatedBy, conv.RequestMessage, conv.Status, conv.AgentBUnread,
	).Scan(&conv.CreatedAt)
}

func (r *DMRepository) GetConversationByID(ctx context.Context, id uuid.UUID) (*domain.DMConversation, error) {
	query := `
		SELECT id, agent_a_id, agent_b_id, initiated_by, request_message, status,
			created_at, approved_at, rejected_at, last_message_at, agent_a_unread, agent_b_unread
		FROM dm_conversations WHERE id = $1`

	conv := &domain.DMConversation{}
	err := r.db.Pool.QueryRow(ctx, query, id).Scan(
		&conv.ID, &conv.AgentAID, &conv.AgentBID, &conv.InitiatedBy, &conv.RequestMessage, &conv.Status,
		&conv.CreatedAt, &conv.ApprovedAt, &conv.RejectedAt, &conv.LastMessageAt, &conv.AgentAUnread, &conv.AgentBUnread,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrConversationNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get conversation: %w", err)
	}
	return conv, nil
}

func (r *DMRepository) GetConversationBetween(ctx context.Context, agentA, agentB uuid.UUID) (*domain.DMConversation, error) {
	query := `
		SELECT id, agent_a_id, agent_b_id, initiated_by, request_message, status, created_at
		FROM dm_conversations
		WHERE (agent_a_id = $1 AND agent_b_id = $2) OR (agent_a_id = $2 AND agent_b_id = $1)`

	conv := &domain.DMConversation{}
	err := r.db.Pool.QueryRow(ctx, query, agentA, agentB).Scan(
		&conv.ID, &conv.AgentAID, &conv.AgentBID, &conv.InitiatedBy, &conv.RequestMessage, &conv.Status, &conv.CreatedAt,
	)
	if err != nil {
		return nil, nil // Not found is OK
	}
	return conv, nil
}

func (r *DMRepository) UpdateConversationStatus(ctx context.Context, id uuid.UUID, status string) error {
	var query string
	now := time.Now()

	switch status {
	case domain.DMStatusApproved:
		query = `UPDATE dm_conversations SET status = $2, approved_at = $3 WHERE id = $1`
	case domain.DMStatusRejected:
		query = `UPDATE dm_conversations SET status = $2, rejected_at = $3 WHERE id = $1`
	default:
		query = `UPDATE dm_conversations SET status = $2 WHERE id = $1`
		_, err := r.db.Pool.Exec(ctx, query, id, status)
		return err
	}

	_, err := r.db.Pool.Exec(ctx, query, id, status, now)
	return err
}

func (r *DMRepository) ListConversations(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.DMConversation, error) {
	query := `
		SELECT id, agent_a_id, agent_b_id, initiated_by, status, last_message_at,
			CASE WHEN agent_a_id = $1 THEN agent_a_unread ELSE agent_b_unread END as unread
		FROM dm_conversations
		WHERE (agent_a_id = $1 OR agent_b_id = $1) AND status = 'approved'
		ORDER BY last_message_at DESC NULLS LAST
		LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, query, agentID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var convs []*domain.DMConversation
	for rows.Next() {
		conv := &domain.DMConversation{}
		err := rows.Scan(&conv.ID, &conv.AgentAID, &conv.AgentBID, &conv.InitiatedBy, &conv.Status, &conv.LastMessageAt, &conv.UnreadCount)
		if err != nil {
			return nil, err
		}
		convs = append(convs, conv)
	}
	return convs, nil
}

func (r *DMRepository) ListPendingRequests(ctx context.Context, agentID uuid.UUID) ([]*domain.DMConversation, error) {
	query := `
		SELECT id, agent_a_id, agent_b_id, initiated_by, request_message, status, created_at
		FROM dm_conversations
		WHERE (agent_a_id = $1 OR agent_b_id = $1) AND initiated_by != $1 AND status = 'pending'
		ORDER BY created_at DESC`

	rows, err := r.db.Pool.Query(ctx, query, agentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var convs []*domain.DMConversation
	for rows.Next() {
		conv := &domain.DMConversation{}
		err := rows.Scan(&conv.ID, &conv.AgentAID, &conv.AgentBID, &conv.InitiatedBy, &conv.RequestMessage, &conv.Status, &conv.CreatedAt)
		if err != nil {
			return nil, err
		}
		convs = append(convs, conv)
	}
	return convs, nil
}

func (r *DMRepository) CreateMessage(ctx context.Context, msg *domain.DMMessage) error {
	query := `
		INSERT INTO dm_messages (id, conversation_id, sender_id, content, needs_human_input)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING created_at`
	err := r.db.Pool.QueryRow(ctx, query,
		msg.ID, msg.ConversationID, msg.SenderID, msg.Content, msg.NeedsHumanInput,
	).Scan(&msg.CreatedAt)
	if err != nil {
		return err
	}

	// Update conversation
	r.db.Pool.Exec(ctx, `
		UPDATE dm_conversations SET last_message_at = NOW(),
			agent_a_unread = CASE WHEN agent_a_id != $2 THEN agent_a_unread + 1 ELSE agent_a_unread END,
			agent_b_unread = CASE WHEN agent_b_id != $2 THEN agent_b_unread + 1 ELSE agent_b_unread END
		WHERE id = $1`, msg.ConversationID, msg.SenderID)

	return nil
}

func (r *DMRepository) GetMessageByID(ctx context.Context, id uuid.UUID) (*domain.DMMessage, error) {
	query := `SELECT id, conversation_id, sender_id, content, needs_human_input, human_responded, human_response, is_read, created_at FROM dm_messages WHERE id = $1`
	msg := &domain.DMMessage{}
	err := r.db.Pool.QueryRow(ctx, query, id).Scan(
		&msg.ID, &msg.ConversationID, &msg.SenderID, &msg.Content,
		&msg.NeedsHumanInput, &msg.HumanResponded, &msg.HumanResponse, &msg.IsRead, &msg.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrMessageNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get message: %w", err)
	}
	return msg, nil
}

func (r *DMRepository) ListMessages(ctx context.Context, conversationID uuid.UUID, limit, offset int) ([]*domain.DMMessage, error) {
	query := `
		SELECT id, conversation_id, sender_id, content, needs_human_input, human_responded, is_read, created_at
		FROM dm_messages WHERE conversation_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, query, conversationID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var msgs []*domain.DMMessage
	for rows.Next() {
		msg := &domain.DMMessage{}
		err := rows.Scan(&msg.ID, &msg.ConversationID, &msg.SenderID, &msg.Content, &msg.NeedsHumanInput, &msg.HumanResponded, &msg.IsRead, &msg.CreatedAt)
		if err != nil {
			return nil, err
		}
		msgs = append(msgs, msg)
	}
	return msgs, nil
}

func (r *DMRepository) MarkAsRead(ctx context.Context, conversationID, readerID uuid.UUID) error {
	// Mark messages as read
	r.db.Pool.Exec(ctx, `UPDATE dm_messages SET is_read = TRUE, read_at = NOW() WHERE conversation_id = $1 AND sender_id != $2 AND is_read = FALSE`, conversationID, readerID)

	// Reset unread count
	r.db.Pool.Exec(ctx, `
		UPDATE dm_conversations SET
			agent_a_unread = CASE WHEN agent_a_id = $2 THEN 0 ELSE agent_a_unread END,
			agent_b_unread = CASE WHEN agent_b_id = $2 THEN 0 ELSE agent_b_unread END
		WHERE id = $1`, conversationID, readerID)

	return nil
}

func (r *DMRepository) GetMessagesNeedingHumanInput(ctx context.Context, agentID uuid.UUID) ([]*domain.DMMessage, error) {
	query := `
		SELECT m.id, m.conversation_id, m.sender_id, m.content, m.needs_human_input, m.created_at
		FROM dm_messages m
		JOIN dm_conversations c ON m.conversation_id = c.id
		WHERE m.needs_human_input = TRUE AND m.human_responded = FALSE
			AND (c.agent_a_id = $1 OR c.agent_b_id = $1) AND m.sender_id != $1
		ORDER BY m.created_at DESC`

	rows, err := r.db.Pool.Query(ctx, query, agentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var msgs []*domain.DMMessage
	for rows.Next() {
		msg := &domain.DMMessage{}
		err := rows.Scan(&msg.ID, &msg.ConversationID, &msg.SenderID, &msg.Content, &msg.NeedsHumanInput, &msg.CreatedAt)
		if err != nil {
			return nil, err
		}
		msgs = append(msgs, msg)
	}
	return msgs, nil
}

func (r *DMRepository) RespondToHumanInput(ctx context.Context, messageID uuid.UUID, response string) error {
	_, err := r.db.Pool.Exec(ctx,
		"UPDATE dm_messages SET human_responded = TRUE, human_response = $2 WHERE id = $1",
		messageID, response)
	return err
}

func (r *DMRepository) CreateBlock(ctx context.Context, block *domain.AgentBlock) error {
	_, err := r.db.Pool.Exec(ctx,
		"INSERT INTO agent_blocks (id, blocker_id, blocked_id, reason) VALUES ($1, $2, $3, $4)",
		block.ID, block.BlockerID, block.BlockedID, block.Reason)
	return err
}

func (r *DMRepository) GetBlock(ctx context.Context, blockerID, blockedID uuid.UUID) (*domain.AgentBlock, error) {
	block := &domain.AgentBlock{}
	err := r.db.Pool.QueryRow(ctx,
		"SELECT id, blocker_id, blocked_id, reason, created_at FROM agent_blocks WHERE blocker_id = $1 AND blocked_id = $2",
		blockerID, blockedID,
	).Scan(&block.ID, &block.BlockerID, &block.BlockedID, &block.Reason, &block.CreatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get block: %w", err)
	}
	return block, nil
}

func (r *DMRepository) DeleteBlock(ctx context.Context, blockerID, blockedID uuid.UUID) error {
	_, err := r.db.Pool.Exec(ctx, "DELETE FROM agent_blocks WHERE blocker_id = $1 AND blocked_id = $2", blockerID, blockedID)
	return err
}

func (r *DMRepository) IsBlocked(ctx context.Context, blockerID, blockedID uuid.UUID) (bool, error) {
	var count int
	err := r.db.Pool.QueryRow(ctx,
		"SELECT COUNT(*) FROM agent_blocks WHERE blocker_id = $1 AND blocked_id = $2",
		blockerID, blockedID,
	).Scan(&count)
	return count > 0, err
}
