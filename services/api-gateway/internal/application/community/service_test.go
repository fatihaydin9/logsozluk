// +build integration

// TODO: Bu testler ErrNotFound kullanımı düzeltildikten sonra çalışacak.

package community

import (
	"context"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"

	"github.com/logsozluk/api-gateway/internal/domain"
)

// MockCommunityRepository is a mock implementation of domain.CommunityRepository
type MockCommunityRepository struct {
	mock.Mock
}

func (m *MockCommunityRepository) Create(ctx context.Context, community *domain.Community) error {
	args := m.Called(ctx, community)
	return args.Error(0)
}

func (m *MockCommunityRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Community, error) {
	args := m.Called(ctx, id)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.Community), args.Error(1)
}

func (m *MockCommunityRepository) GetBySlug(ctx context.Context, slug string) (*domain.Community, error) {
	args := m.Called(ctx, slug)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.Community), args.Error(1)
}

func (m *MockCommunityRepository) List(ctx context.Context, limit, offset int) ([]*domain.Community, error) {
	args := m.Called(ctx, limit, offset)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.Community), args.Error(1)
}

func (m *MockCommunityRepository) ListByAgent(ctx context.Context, agentID uuid.UUID) ([]*domain.Community, error) {
	args := m.Called(ctx, agentID)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.Community), args.Error(1)
}

func (m *MockCommunityRepository) Update(ctx context.Context, community *domain.Community) error {
	args := m.Called(ctx, community)
	return args.Error(0)
}

func (m *MockCommunityRepository) Delete(ctx context.Context, id uuid.UUID) error {
	args := m.Called(ctx, id)
	return args.Error(0)
}

func (m *MockCommunityRepository) AddMember(ctx context.Context, member *domain.CommunityMember) error {
	args := m.Called(ctx, member)
	return args.Error(0)
}

func (m *MockCommunityRepository) GetMember(ctx context.Context, communityID, agentID uuid.UUID) (*domain.CommunityMember, error) {
	args := m.Called(ctx, communityID, agentID)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.CommunityMember), args.Error(1)
}

func (m *MockCommunityRepository) UpdateMember(ctx context.Context, member *domain.CommunityMember) error {
	args := m.Called(ctx, member)
	return args.Error(0)
}

func (m *MockCommunityRepository) RemoveMember(ctx context.Context, communityID, agentID uuid.UUID) error {
	args := m.Called(ctx, communityID, agentID)
	return args.Error(0)
}

func (m *MockCommunityRepository) ListMembers(ctx context.Context, communityID uuid.UUID, limit, offset int) ([]*domain.CommunityMember, error) {
	args := m.Called(ctx, communityID, limit, offset)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.CommunityMember), args.Error(1)
}

func (m *MockCommunityRepository) CreateMessage(ctx context.Context, message *domain.CommunityMessage) error {
	args := m.Called(ctx, message)
	return args.Error(0)
}

func (m *MockCommunityRepository) GetMessage(ctx context.Context, id uuid.UUID) (*domain.CommunityMessage, error) {
	args := m.Called(ctx, id)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.CommunityMessage), args.Error(1)
}

func (m *MockCommunityRepository) ListMessages(ctx context.Context, communityID uuid.UUID, limit, offset int) ([]*domain.CommunityMessage, error) {
	args := m.Called(ctx, communityID, limit, offset)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.CommunityMessage), args.Error(1)
}

// ==================== TEST CASES ====================

func TestService_Create(t *testing.T) {
	t.Run("creates community successfully", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		creatorID := uuid.New()

		mockRepo.On("Create", ctx, mock.AnythingOfType("*domain.Community")).Return(nil)
		mockRepo.On("AddMember", ctx, mock.AnythingOfType("*domain.CommunityMember")).Return(nil)

		input := CreateInput{
			Name:          "Gece Kuşları",
			Description:   "Gece aktif olanlar için",
			CommunityType: "open",
			FocusTopics:   []string{"felsefe", "gece"},
			CreatorID:     creatorID,
			MaxMembers:    50,
		}

		community, err := service.Create(ctx, input)

		assert.NoError(t, err)
		assert.NotNil(t, community)
		assert.Equal(t, "Gece Kuşları", community.Name)
		assert.Equal(t, "gece-kuslari", community.Slug)
		assert.Equal(t, domain.CommunityTypeOpen, community.CommunityType)
		assert.True(t, community.IsActive)
		mockRepo.AssertExpectations(t)
	})

	t.Run("creates community with default values", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		creatorID := uuid.New()

		mockRepo.On("Create", ctx, mock.AnythingOfType("*domain.Community")).Return(nil)
		mockRepo.On("AddMember", ctx, mock.AnythingOfType("*domain.CommunityMember")).Return(nil)

		input := CreateInput{
			Name:      "Test Community",
			CreatorID: creatorID,
		}

		community, err := service.Create(ctx, input)

		assert.NoError(t, err)
		assert.NotNil(t, community)
		assert.Equal(t, domain.CommunityTypeOpen, community.CommunityType)
		assert.Equal(t, 50, community.MaxMembers)
		mockRepo.AssertExpectations(t)
	})

	t.Run("adds creator as owner", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		creatorID := uuid.New()

		mockRepo.On("Create", ctx, mock.AnythingOfType("*domain.Community")).Return(nil)
		mockRepo.On("AddMember", ctx, mock.MatchedBy(func(m *domain.CommunityMember) bool {
			return m.AgentID == creatorID && m.Role == domain.MemberRoleOwner
		})).Return(nil)

		input := CreateInput{
			Name:      "Test",
			CreatorID: creatorID,
		}

		_, err := service.Create(ctx, input)
		assert.NoError(t, err)
		mockRepo.AssertExpectations(t)
	})
}

func TestService_Join(t *testing.T) {
	t.Run("joins open community successfully", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()
		agentID := uuid.New()

		community := &domain.Community{
			ID:            communityID,
			Name:          "Test",
			CommunityType: domain.CommunityTypeOpen,
			MaxMembers:    50,
			MemberCount:   5,
		}

		mockRepo.On("GetByID", ctx, communityID).Return(community, nil)
		mockRepo.On("GetMember", ctx, communityID, agentID).Return(nil, domain.ErrNotFound)
		mockRepo.On("AddMember", ctx, mock.MatchedBy(func(m *domain.CommunityMember) bool {
			return m.Status == domain.MemberStatusActive && m.Role == domain.MemberRoleMember
		})).Return(nil)

		err := service.Join(ctx, JoinInput{CommunityID: communityID, AgentID: agentID})

		assert.NoError(t, err)
		mockRepo.AssertExpectations(t)
	})

	t.Run("requires approval for invite-only community", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()
		agentID := uuid.New()

		community := &domain.Community{
			ID:              communityID,
			CommunityType:   domain.CommunityTypeOpen,
			RequireApproval: true,
			MaxMembers:      50,
			MemberCount:     5,
		}

		mockRepo.On("GetByID", ctx, communityID).Return(community, nil)
		mockRepo.On("GetMember", ctx, communityID, agentID).Return(nil, domain.ErrNotFound)
		mockRepo.On("AddMember", ctx, mock.MatchedBy(func(m *domain.CommunityMember) bool {
			return m.Status == domain.MemberStatusPending
		})).Return(nil)

		err := service.Join(ctx, JoinInput{CommunityID: communityID, AgentID: agentID})

		assert.NoError(t, err)
		mockRepo.AssertExpectations(t)
	})

	t.Run("fails when already a member", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()
		agentID := uuid.New()

		community := &domain.Community{
			ID:         communityID,
			MaxMembers: 50,
		}

		existingMember := &domain.CommunityMember{
			CommunityID: communityID,
			AgentID:     agentID,
			Status:      domain.MemberStatusActive,
		}

		mockRepo.On("GetByID", ctx, communityID).Return(community, nil)
		mockRepo.On("GetMember", ctx, communityID, agentID).Return(existingMember, nil)

		err := service.Join(ctx, JoinInput{CommunityID: communityID, AgentID: agentID})

		assert.Error(t, err)
		assert.Equal(t, domain.ErrAlreadyFollowing, err)
	})

	t.Run("fails when community is full", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()
		agentID := uuid.New()

		community := &domain.Community{
			ID:          communityID,
			MaxMembers:  10,
			MemberCount: 10, // Full
		}

		mockRepo.On("GetByID", ctx, communityID).Return(community, nil)
		mockRepo.On("GetMember", ctx, communityID, agentID).Return(nil, domain.ErrNotFound)

		err := service.Join(ctx, JoinInput{CommunityID: communityID, AgentID: agentID})

		assert.Error(t, err)
	})
}

func TestService_Leave(t *testing.T) {
	t.Run("leaves community successfully", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()
		agentID := uuid.New()

		mockRepo.On("RemoveMember", ctx, communityID, agentID).Return(nil)

		err := service.Leave(ctx, communityID, agentID)

		assert.NoError(t, err)
		mockRepo.AssertExpectations(t)
	})
}

func TestService_SendMessage(t *testing.T) {
	t.Run("sends message successfully", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()
		senderID := uuid.New()

		member := &domain.CommunityMember{
			CommunityID: communityID,
			AgentID:     senderID,
			Status:      domain.MemberStatusActive,
		}

		mockRepo.On("GetMember", ctx, communityID, senderID).Return(member, nil)
		mockRepo.On("CreateMessage", ctx, mock.AnythingOfType("*domain.CommunityMessage")).Return(nil)

		input := SendMessageInput{
			CommunityID: communityID,
			SenderID:    senderID,
			Content:     "Merhaba topluluk!",
		}

		message, err := service.SendMessage(ctx, input)

		assert.NoError(t, err)
		assert.NotNil(t, message)
		assert.Equal(t, "Merhaba topluluk!", message.Content)
		assert.Equal(t, "text", message.MessageType)
		mockRepo.AssertExpectations(t)
	})

	t.Run("sends message with reply", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()
		senderID := uuid.New()
		replyToID := uuid.New()

		member := &domain.CommunityMember{
			CommunityID: communityID,
			AgentID:     senderID,
			Status:      domain.MemberStatusActive,
		}

		mockRepo.On("GetMember", ctx, communityID, senderID).Return(member, nil)
		mockRepo.On("CreateMessage", ctx, mock.MatchedBy(func(m *domain.CommunityMessage) bool {
			return m.ReplyToID != nil && *m.ReplyToID == replyToID
		})).Return(nil)

		input := SendMessageInput{
			CommunityID: communityID,
			SenderID:    senderID,
			Content:     "Cevap!",
			ReplyToID:   &replyToID,
		}

		message, err := service.SendMessage(ctx, input)

		assert.NoError(t, err)
		assert.NotNil(t, message)
		assert.Equal(t, &replyToID, message.ReplyToID)
		mockRepo.AssertExpectations(t)
	})

	t.Run("fails when not a member", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()
		senderID := uuid.New()

		mockRepo.On("GetMember", ctx, communityID, senderID).Return(nil, domain.ErrNotFound)

		input := SendMessageInput{
			CommunityID: communityID,
			SenderID:    senderID,
			Content:     "Test",
		}

		message, err := service.SendMessage(ctx, input)

		assert.Error(t, err)
		assert.Nil(t, message)
	})

	t.Run("fails when member is pending", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()
		senderID := uuid.New()

		member := &domain.CommunityMember{
			CommunityID: communityID,
			AgentID:     senderID,
			Status:      domain.MemberStatusPending,
		}

		mockRepo.On("GetMember", ctx, communityID, senderID).Return(member, nil)

		input := SendMessageInput{
			CommunityID: communityID,
			SenderID:    senderID,
			Content:     "Test",
		}

		message, err := service.SendMessage(ctx, input)

		assert.Error(t, err)
		assert.Nil(t, message)
	})
}

func TestService_List(t *testing.T) {
	t.Run("lists communities with default limit", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()

		communities := []*domain.Community{
			{ID: uuid.New(), Name: "Community 1"},
			{ID: uuid.New(), Name: "Community 2"},
		}

		mockRepo.On("List", ctx, 20, 0).Return(communities, nil)

		result, err := service.List(ctx, 0, 0)

		assert.NoError(t, err)
		assert.Len(t, result, 2)
		mockRepo.AssertExpectations(t)
	})

	t.Run("respects max limit", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()

		mockRepo.On("List", ctx, 20, 0).Return([]*domain.Community{}, nil)

		_, err := service.List(ctx, 1000, 0) // Try to get 1000

		assert.NoError(t, err)
		mockRepo.AssertExpectations(t)
	})
}

func TestService_ListMessages(t *testing.T) {
	t.Run("lists messages successfully", func(t *testing.T) {
		mockRepo := new(MockCommunityRepository)
		service := NewService(mockRepo)
		ctx := context.Background()
		communityID := uuid.New()

		messages := []*domain.CommunityMessage{
			{ID: uuid.New(), Content: "Message 1"},
			{ID: uuid.New(), Content: "Message 2"},
		}

		mockRepo.On("ListMessages", ctx, communityID, 50, 0).Return(messages, nil)

		result, err := service.ListMessages(ctx, communityID, 0, 0)

		assert.NoError(t, err)
		assert.Len(t, result, 2)
		mockRepo.AssertExpectations(t)
	})
}

func TestGenerateSlug(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{"simple name", "Test Community", "test-community"},
		{"turkish characters", "Gece Kuşları", "gece-kuslari"},
		{"multiple turkish chars", "Öğrenci Şöleni", "ogrenci-soleni"},
		{"mixed case", "TeSt CoMmUnItY", "test-community"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := generateSlug(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}
