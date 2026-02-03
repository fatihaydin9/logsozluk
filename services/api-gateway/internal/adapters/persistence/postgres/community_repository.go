package postgres

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// CommunityRepository implements domain.CommunityRepository
type CommunityRepository struct {
	db *DB
}

// NewCommunityRepository creates a new community repository
func NewCommunityRepository(db *DB) *CommunityRepository {
	return &CommunityRepository{db: db}
}

// Create creates a new community
func (r *CommunityRepository) Create(ctx context.Context, c *domain.Community) error {
	query := `
		INSERT INTO agent_communities (id, name, slug, description, community_type, focus_topics, 
			created_by, max_members, require_approval, is_active)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	`
	_, err := r.db.Pool.Exec(ctx, query,
		c.ID, c.Name, c.Slug, c.Description, c.CommunityType, c.FocusTopics,
		c.CreatedBy, c.MaxMembers, c.RequireApproval, c.IsActive,
	)
	if err != nil {
		return fmt.Errorf("failed to create community: %w", err)
	}
	return nil
}

// GetByID retrieves a community by ID
func (r *CommunityRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Community, error) {
	query := `
		SELECT c.id, c.name, c.slug, c.description, c.community_type, c.focus_topics,
			c.created_by, c.max_members, c.require_approval, c.member_count, c.message_count,
			c.last_activity_at, c.is_active, c.created_at, c.updated_at,
			a.id, a.username, a.display_name, a.bio, a.avatar_url
		FROM agent_communities c
		LEFT JOIN agents a ON c.created_by = a.id
		WHERE c.id = $1 AND c.is_active = true
	`
	row := r.db.Pool.QueryRow(ctx, query, id)
	return r.scanCommunityWithCreator(row)
}

// GetBySlug retrieves a community by slug
func (r *CommunityRepository) GetBySlug(ctx context.Context, slug string) (*domain.Community, error) {
	query := `
		SELECT c.id, c.name, c.slug, c.description, c.community_type, c.focus_topics,
			c.created_by, c.max_members, c.require_approval, c.member_count, c.message_count,
			c.last_activity_at, c.is_active, c.created_at, c.updated_at,
			a.id, a.username, a.display_name, a.bio, a.avatar_url
		FROM agent_communities c
		LEFT JOIN agents a ON c.created_by = a.id
		WHERE c.slug = $1 AND c.is_active = true
	`
	row := r.db.Pool.QueryRow(ctx, query, slug)
	return r.scanCommunityWithCreator(row)
}

// Update updates a community
func (r *CommunityRepository) Update(ctx context.Context, c *domain.Community) error {
	query := `
		UPDATE agent_communities 
		SET name = $2, description = $3, community_type = $4, focus_topics = $5,
			max_members = $6, require_approval = $7, updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.db.Pool.Exec(ctx, query,
		c.ID, c.Name, c.Description, c.CommunityType, c.FocusTopics,
		c.MaxMembers, c.RequireApproval,
	)
	if err != nil {
		return fmt.Errorf("failed to update community: %w", err)
	}
	return nil
}

// List lists all communities with pagination
func (r *CommunityRepository) List(ctx context.Context, limit, offset int) ([]*domain.Community, error) {
	query := `
		SELECT c.id, c.name, c.slug, c.description, c.community_type, c.focus_topics,
			c.created_by, c.max_members, c.require_approval, c.member_count, c.message_count,
			c.last_activity_at, c.is_active, c.created_at, c.updated_at,
			a.id, a.username, a.display_name, a.bio, a.avatar_url
		FROM agent_communities c
		LEFT JOIN agents a ON c.created_by = a.id
		WHERE c.is_active = true
		ORDER BY c.last_activity_at DESC
		LIMIT $1 OFFSET $2
	`
	rows, err := r.db.Pool.Query(ctx, query, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list communities: %w", err)
	}
	defer rows.Close()

	var communities []*domain.Community
	for rows.Next() {
		c, err := r.scanCommunityWithCreatorFromRows(rows)
		if err != nil {
			return nil, err
		}
		communities = append(communities, c)
	}
	return communities, nil
}

// ListByAgent lists communities an agent is a member of
func (r *CommunityRepository) ListByAgent(ctx context.Context, agentID uuid.UUID) ([]*domain.Community, error) {
	query := `
		SELECT c.id, c.name, c.slug, c.description, c.community_type, c.focus_topics,
			c.created_by, c.max_members, c.require_approval, c.member_count, c.message_count,
			c.last_activity_at, c.is_active, c.created_at, c.updated_at,
			a.id, a.username, a.display_name, a.bio, a.avatar_url
		FROM agent_communities c
		LEFT JOIN agents a ON c.created_by = a.id
		INNER JOIN agent_community_members m ON c.id = m.community_id
		WHERE m.agent_id = $1 AND m.status = 'active' AND c.is_active = true
		ORDER BY c.last_activity_at DESC
	`
	rows, err := r.db.Pool.Query(ctx, query, agentID)
	if err != nil {
		return nil, fmt.Errorf("failed to list communities by agent: %w", err)
	}
	defer rows.Close()

	var communities []*domain.Community
	for rows.Next() {
		c, err := r.scanCommunityWithCreatorFromRows(rows)
		if err != nil {
			return nil, err
		}
		communities = append(communities, c)
	}
	return communities, nil
}

// AddMember adds a member to a community
func (r *CommunityRepository) AddMember(ctx context.Context, m *domain.CommunityMember) error {
	query := `
		INSERT INTO agent_community_members (community_id, agent_id, role, status, joined_at)
		VALUES ($1, $2, $3, $4, NOW())
		ON CONFLICT (community_id, agent_id) DO UPDATE SET status = $4, role = $3
	`
	_, err := r.db.Pool.Exec(ctx, query, m.CommunityID, m.AgentID, m.Role, m.Status)
	if err != nil {
		return fmt.Errorf("failed to add member: %w", err)
	}

	// Update member count
	_, err = r.db.Pool.Exec(ctx, `
		UPDATE agent_communities SET member_count = (
			SELECT COUNT(*) FROM agent_community_members WHERE community_id = $1 AND status = 'active'
		) WHERE id = $1
	`, m.CommunityID)
	return err
}

// GetMember gets a member from a community
func (r *CommunityRepository) GetMember(ctx context.Context, communityID, agentID uuid.UUID) (*domain.CommunityMember, error) {
	query := `
		SELECT m.community_id, m.agent_id, m.role, m.status, m.messages_sent, 
			m.last_read_at, m.last_message_at, m.joined_at,
			a.id, a.username, a.display_name, a.bio, a.avatar_url
		FROM agent_community_members m
		LEFT JOIN agents a ON m.agent_id = a.id
		WHERE m.community_id = $1 AND m.agent_id = $2
	`
	row := r.db.Pool.QueryRow(ctx, query, communityID, agentID)

	var m domain.CommunityMember
	var agent domain.Agent
	err := row.Scan(
		&m.CommunityID, &m.AgentID, &m.Role, &m.Status, &m.MessagesSent,
		&m.LastReadAt, &m.LastMessageAt, &m.JoinedAt,
		&agent.ID, &agent.Username, &agent.DisplayName, &agent.Bio, &agent.AvatarURL,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get member: %w", err)
	}
	m.Agent = &agent
	return &m, nil
}

// UpdateMember updates a member's role or status
func (r *CommunityRepository) UpdateMember(ctx context.Context, m *domain.CommunityMember) error {
	query := `
		UPDATE agent_community_members 
		SET role = $3, status = $4
		WHERE community_id = $1 AND agent_id = $2
	`
	_, err := r.db.Pool.Exec(ctx, query, m.CommunityID, m.AgentID, m.Role, m.Status)
	return err
}

// RemoveMember removes a member from a community
func (r *CommunityRepository) RemoveMember(ctx context.Context, communityID, agentID uuid.UUID) error {
	query := `UPDATE agent_community_members SET status = 'left' WHERE community_id = $1 AND agent_id = $2`
	_, err := r.db.Pool.Exec(ctx, query, communityID, agentID)
	return err
}

// ListMembers lists members of a community
func (r *CommunityRepository) ListMembers(ctx context.Context, communityID uuid.UUID, limit, offset int) ([]*domain.CommunityMember, error) {
	query := `
		SELECT m.community_id, m.agent_id, m.role, m.status, m.messages_sent,
			m.last_read_at, m.last_message_at, m.joined_at,
			a.id, a.username, a.display_name, a.bio, a.avatar_url
		FROM agent_community_members m
		LEFT JOIN agents a ON m.agent_id = a.id
		WHERE m.community_id = $1 AND m.status = 'active'
		ORDER BY m.joined_at ASC
		LIMIT $2 OFFSET $3
	`
	rows, err := r.db.Pool.Query(ctx, query, communityID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list members: %w", err)
	}
	defer rows.Close()

	var members []*domain.CommunityMember
	for rows.Next() {
		var m domain.CommunityMember
		var agent domain.Agent
		err := rows.Scan(
			&m.CommunityID, &m.AgentID, &m.Role, &m.Status, &m.MessagesSent,
			&m.LastReadAt, &m.LastMessageAt, &m.JoinedAt,
			&agent.ID, &agent.Username, &agent.DisplayName, &agent.Bio, &agent.AvatarURL,
		)
		if err != nil {
			return nil, err
		}
		m.Agent = &agent
		members = append(members, &m)
	}
	return members, nil
}

// CreateMessage creates a message in a community
func (r *CommunityRepository) CreateMessage(ctx context.Context, m *domain.CommunityMessage) error {
	query := `
		INSERT INTO agent_community_messages (id, community_id, sender_id, content, message_type, reply_to_id)
		VALUES ($1, $2, $3, $4, $5, $6)
	`
	_, err := r.db.Pool.Exec(ctx, query, m.ID, m.CommunityID, m.SenderID, m.Content, m.MessageType, m.ReplyToID)
	if err != nil {
		return fmt.Errorf("failed to create message: %w", err)
	}

	// Update community activity
	_, err = r.db.Pool.Exec(ctx, `
		UPDATE agent_communities SET message_count = message_count + 1, last_activity_at = NOW() WHERE id = $1
	`, m.CommunityID)
	return err
}

// ListMessages lists messages in a community
func (r *CommunityRepository) ListMessages(ctx context.Context, communityID uuid.UUID, limit, offset int) ([]*domain.CommunityMessage, error) {
	query := `
		SELECT m.id, m.community_id, m.sender_id, m.content, m.message_type, m.reply_to_id, m.created_at,
			a.id, a.username, a.display_name, a.bio, a.avatar_url
		FROM agent_community_messages m
		LEFT JOIN agents a ON m.sender_id = a.id
		WHERE m.community_id = $1
		ORDER BY m.created_at DESC
		LIMIT $2 OFFSET $3
	`
	rows, err := r.db.Pool.Query(ctx, query, communityID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list messages: %w", err)
	}
	defer rows.Close()

	var messages []*domain.CommunityMessage
	for rows.Next() {
		var m domain.CommunityMessage
		var sender domain.Agent
		err := rows.Scan(
			&m.ID, &m.CommunityID, &m.SenderID, &m.Content, &m.MessageType, &m.ReplyToID, &m.CreatedAt,
			&sender.ID, &sender.Username, &sender.DisplayName, &sender.Bio, &sender.AvatarURL,
		)
		if err != nil {
			return nil, err
		}
		m.Sender = &sender
		messages = append(messages, &m)
	}
	return messages, nil
}

// Helper functions
func (r *CommunityRepository) scanCommunityWithCreator(row interface{ Scan(...interface{}) error }) (*domain.Community, error) {
	var c domain.Community
	var creator domain.Agent
	var focusTopics []string

	err := row.Scan(
		&c.ID, &c.Name, &c.Slug, &c.Description, &c.CommunityType, &focusTopics,
		&c.CreatedBy, &c.MaxMembers, &c.RequireApproval, &c.MemberCount, &c.MessageCount,
		&c.LastActivityAt, &c.IsActive, &c.CreatedAt, &c.UpdatedAt,
		&creator.ID, &creator.Username, &creator.DisplayName, &creator.Bio, &creator.AvatarURL,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to scan community: %w", err)
	}
	c.FocusTopics = focusTopics
	c.Creator = &creator
	return &c, nil
}

func (r *CommunityRepository) scanCommunityWithCreatorFromRows(rows interface{ Scan(...interface{}) error }) (*domain.Community, error) {
	return r.scanCommunityWithCreator(rows)
}
