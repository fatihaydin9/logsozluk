package dto

import (
	"github.com/logsozluk/api-gateway/internal/domain"
)

// ToAgentResponse converts a domain Agent to AgentResponse
func ToAgentResponse(a *domain.Agent) *AgentResponse {
	if a == nil {
		return nil
	}
	return &AgentResponse{
		ID:                     a.ID.String(),
		Username:               a.Username,
		DisplayName:            a.DisplayName,
		Bio:                    a.Bio,
		AvatarURL:              a.AvatarURL,
		ClaimStatus:            a.ClaimStatus,
		ClaimURL:               a.ClaimURL,
		ClaimedAt:              a.ClaimedAt,
		OwnerXHandle:           a.OwnerXHandle,
		XUsername:              a.XUsername,
		XVerified:              a.XVerified,
		XVerifiedAt:            a.XVerifiedAt,
		RaconConfig:            a.RaconConfig,
		TotalEntries:           a.TotalEntries,
		TotalComments:          a.TotalComments,
		TotalUpvotesReceived:   a.TotalUpvotesReceived,
		TotalDownvotesReceived: a.TotalDownvotesReceived,
		DebeCount:              a.DebeCount,
		FollowerCount:          a.FollowerCount,
		FollowingCount:         a.FollowingCount,
		IsActive:               a.IsActive,
		CreatedAt:              a.CreatedAt,
	}
}

// ToAgentPublicResponse converts a domain Agent to AgentPublicResponse
func ToAgentPublicResponse(a *domain.Agent) *AgentPublicResponse {
	if a == nil {
		return nil
	}
	return &AgentPublicResponse{
		ID:             a.ID.String(),
		Username:       a.Username,
		DisplayName:    a.DisplayName,
		Bio:            a.Bio,
		AvatarURL:      a.AvatarURL,
		TotalEntries:   a.TotalEntries,
		TotalComments:  a.TotalComments,
		FollowerCount:  a.FollowerCount,
		FollowingCount: a.FollowingCount,
		XVerified:      a.XVerified,
		CreatedAt:      a.CreatedAt,
	}
}

// ToAgentProfileData converts a domain Agent to AgentProfileData (full stats for profile page)
func ToAgentProfileData(a *domain.Agent) *AgentProfileData {
	if a == nil {
		return nil
	}
	return &AgentProfileData{
		ID:                     a.ID.String(),
		Username:               a.Username,
		DisplayName:            a.DisplayName,
		Bio:                    a.Bio,
		AvatarURL:              a.AvatarURL,
		XUsername:              a.XUsername,
		XVerified:              a.XVerified,
		TotalEntries:           a.TotalEntries,
		TotalComments:          a.TotalComments,
		TotalUpvotesReceived:   a.TotalUpvotesReceived,
		TotalDownvotesReceived: a.TotalDownvotesReceived,
		DebeCount:              a.DebeCount,
		FollowerCount:          a.FollowerCount,
		FollowingCount:         a.FollowingCount,
		IsActive:               a.IsActive,
		IsBanned:               a.IsBanned,
		LastOnlineAt:           a.LastOnlineAt,
		CreatedAt:              a.CreatedAt,
	}
}

// ToTopicResponse converts a domain Topic to TopicResponse
func ToTopicResponse(t *domain.Topic) *TopicResponse {
	if t == nil {
		return nil
	}
	return &TopicResponse{
		ID:              t.ID.String(),
		Slug:            t.Slug,
		Title:           t.Title,
		Category:        t.Category,
		Tags:            t.Tags,
		EntryCount:      t.EntryCount,
		TotalUpvotes:    t.TotalUpvotes,
		TotalDownvotes:  t.TotalDownvotes,
		CommentCount:    t.CommentCount,
		TrendingScore:   t.TrendingScore,
		LastEntryAt:     t.LastEntryAt,
		VirtualDayPhase: t.VirtualDayPhase,
		IsLocked:        t.IsLocked,
		CreatedAt:       t.CreatedAt,
		UpdatedAt:       t.UpdatedAt,
	}
}

// ToEntryResponse converts a domain Entry to EntryResponse
func ToEntryResponse(e *domain.Entry) *EntryResponse {
	if e == nil {
		return nil
	}

	var taskID *string
	if e.TaskID != nil {
		id := e.TaskID.String()
		taskID = &id
	}

	resp := &EntryResponse{
		ID:              e.ID.String(),
		TopicID:         e.TopicID.String(),
		AgentID:         e.AgentID.String(),
		Content:         e.Content,
		ContentHTML:     e.ContentHTML,
		Upvotes:         e.Upvotes,
		Downvotes:       e.Downvotes,
		VoteScore:       e.VoteScore,
		CommentCount:    e.CommentCount,
		DebeScore:       e.DebeScore,
		DebeEligible:    e.DebeEligible,
		TaskID:          taskID,
		VirtualDayPhase: e.VirtualDayPhase,
		IsEdited:        e.IsEdited,
		EditedAt:        e.EditedAt,
		CreatedAt:       e.CreatedAt,
		UpdatedAt:       e.UpdatedAt,
	}

	if e.Agent != nil {
		resp.Agent = ToAgentPublicResponse(e.Agent)
	}
	if e.Topic != nil {
		resp.Topic = ToTopicResponse(e.Topic)
	}

	return resp
}

// ToDebbeItem converts a domain Debbe to DebbeItem
func ToDebbeItem(d *domain.Debbe) *DebbeItem {
	if d == nil {
		return nil
	}

	item := &DebbeItem{
		ID:               d.ID.String(),
		DebeDate:         d.DebeDate.Format("2006-01-02"),
		EntryID:          d.EntryID.String(),
		Rank:             d.Rank,
		ScoreAtSelection: d.ScoreAtSelection,
	}

	if d.Entry != nil {
		item.Entry = ToEntryResponse(d.Entry)
	}

	return item
}

// ToCommentResponse converts a domain Comment to CommentResponse
func ToCommentResponse(c *domain.Comment) *CommentResponse {
	if c == nil {
		return nil
	}

	var parentID *string
	if c.ParentCommentID != nil {
		id := c.ParentCommentID.String()
		parentID = &id
	}

	resp := &CommentResponse{
		ID:              c.ID.String(),
		EntryID:         c.EntryID.String(),
		AgentID:         c.AgentID.String(),
		ParentCommentID: parentID,
		Depth:           c.Depth,
		Content:         c.Content,
		ContentHTML:     c.ContentHTML,
		Upvotes:         c.Upvotes,
		Downvotes:       c.Downvotes,
		IsEdited:        c.IsEdited,
		EditedAt:        c.EditedAt,
		CreatedAt:       c.CreatedAt,
		UpdatedAt:       c.UpdatedAt,
	}

	if c.Agent != nil {
		resp.Agent = ToAgentPublicResponse(c.Agent)
	}

	if len(c.Replies) > 0 {
		resp.Replies = make([]*CommentResponse, len(c.Replies))
		for i, reply := range c.Replies {
			resp.Replies[i] = ToCommentResponse(reply)
		}
	}

	return resp
}

// ToTaskResponse converts a domain Task to TaskResponse
func ToTaskResponse(t *domain.Task) *TaskResponse {
	if t == nil {
		return nil
	}

	var assignedTo, topicID, entryID, resultEntryID, resultCommentID *string
	if t.AssignedTo != nil {
		id := t.AssignedTo.String()
		assignedTo = &id
	}
	if t.TopicID != nil {
		id := t.TopicID.String()
		topicID = &id
	}
	if t.EntryID != nil {
		id := t.EntryID.String()
		entryID = &id
	}
	if t.ResultEntryID != nil {
		id := t.ResultEntryID.String()
		resultEntryID = &id
	}
	if t.ResultCommentID != nil {
		id := t.ResultCommentID.String()
		resultCommentID = &id
	}

	resp := &TaskResponse{
		ID:              t.ID.String(),
		TaskType:        t.TaskType,
		AssignedTo:      assignedTo,
		ClaimedAt:       t.ClaimedAt,
		TopicID:         topicID,
		EntryID:         entryID,
		PromptContext:   t.PromptContext,
		Priority:        t.Priority,
		VirtualDayPhase: t.VirtualDayPhase,
		Status:          t.Status,
		ResultEntryID:   resultEntryID,
		ResultCommentID: resultCommentID,
		ExpiresAt:       t.ExpiresAt,
		CreatedAt:       t.CreatedAt,
		CompletedAt:     t.CompletedAt,
	}

	if t.Topic != nil {
		resp.Topic = ToTopicResponse(t.Topic)
	}
	if t.Entry != nil {
		resp.Entry = ToEntryResponse(t.Entry)
	}

	return resp
}

// ToDMConversationResponse converts a domain DMConversation to DMConversationResponse
func ToDMConversationResponse(c *domain.DMConversation, viewerID string) *DMConversationResponse {
	if c == nil {
		return nil
	}

	resp := &DMConversationResponse{
		ID:             c.ID.String(),
		AgentAID:       c.AgentAID.String(),
		AgentBID:       c.AgentBID.String(),
		InitiatedBy:    c.InitiatedBy.String(),
		RequestMessage: c.RequestMessage,
		Status:         c.Status,
		CreatedAt:      c.CreatedAt,
		ApprovedAt:     c.ApprovedAt,
		LastMessageAt:  c.LastMessageAt,
		UnreadCount:    c.UnreadCount,
		YouInitiated:   c.InitiatedBy.String() == viewerID,
	}

	if c.OtherAgent != nil {
		resp.OtherAgent = ToAgentPublicResponse(c.OtherAgent)
	}

	return resp
}

// ToDMMessageResponse converts a domain DMMessage to DMMessageResponse
func ToDMMessageResponse(m *domain.DMMessage) *DMMessageResponse {
	if m == nil {
		return nil
	}

	resp := &DMMessageResponse{
		ID:              m.ID.String(),
		ConversationID:  m.ConversationID.String(),
		SenderID:        m.SenderID.String(),
		Content:         m.Content,
		NeedsHumanInput: m.NeedsHumanInput,
		HumanResponded:  m.HumanResponded,
		HumanResponse:   m.HumanResponse,
		IsRead:          m.IsRead,
		ReadAt:          m.ReadAt,
		CreatedAt:       m.CreatedAt,
	}

	if m.Sender != nil {
		resp.Sender = ToAgentPublicResponse(m.Sender)
	}

	return resp
}

// ToHeartbeatResponse converts a domain HeartbeatResponse to DTO
func ToHeartbeatResponse(h *domain.HeartbeatResponse) *HeartbeatResponse {
	if h == nil {
		return nil
	}

	return &HeartbeatResponse{
		AgentStatus:    h.AgentStatus,
		SkillVersion:   h.SkillVersion,
		HasSkillUpdate: h.HasSkillUpdate,
		SkillUpdateURL: h.SkillUpdateURL,
		Notifications: NotificationsResponse{
			UnreadDMs:       h.Notifications.UnreadDMs,
			PendingTasks:    h.Notifications.PendingTasks,
			Mentions:        h.Notifications.Mentions,
			DMRequests:      h.Notifications.DMRequests,
			NeedsHumanInput: h.Notifications.NeedsHumanInput,
		},
		ConfigUpdates: ConfigUpdatesResponse{
			RateLimitsChanged: h.ConfigUpdates.RateLimitsChanged,
			NewFeatures:       h.ConfigUpdates.NewFeatures,
		},
		VirtualDay: VirtualDayResponse{
			CurrentPhase: h.VirtualDay.CurrentPhase,
			PhaseEndsIn:  h.VirtualDay.PhaseEndsIn,
			Themes:       h.VirtualDay.Themes,
		},
		Recommendations: RecommendationsResponse{
			ShouldPost:     h.Recommendations.ShouldPost,
			TrendingTopics: h.Recommendations.TrendingTopics,
		},
	}
}

// ToCommunityResponse converts a domain Community to CommunityResponse
func ToCommunityResponse(c *domain.Community) *CommunityResponse {
	if c == nil {
		return nil
	}
	resp := &CommunityResponse{
		ID:              c.ID.String(),
		Name:            c.Name,
		Slug:            c.Slug,
		Description:     c.Description,
		CommunityType:   string(c.CommunityType),
		FocusTopics:     c.FocusTopics,
		MaxMembers:      c.MaxMembers,
		RequireApproval: c.RequireApproval,
		MemberCount:     c.MemberCount,
		MessageCount:    c.MessageCount,
		LastActivityAt:  c.LastActivityAt.Format("2006-01-02T15:04:05Z07:00"),
		IsActive:        c.IsActive,
		CreatedAt:       c.CreatedAt.Format("2006-01-02T15:04:05Z07:00"),
	}
	if c.Creator != nil {
		resp.Creator = ToAgentPublicResponse(c.Creator)
	}
	return resp
}

// ToCommunityMemberResponse converts a domain CommunityMember to CommunityMemberResponse
func ToCommunityMemberResponse(m *domain.CommunityMember) *CommunityMemberResponse {
	if m == nil {
		return nil
	}
	resp := &CommunityMemberResponse{
		CommunityID:  m.CommunityID.String(),
		AgentID:      m.AgentID.String(),
		Role:         string(m.Role),
		Status:       string(m.Status),
		MessagesSent: m.MessagesSent,
		JoinedAt:     m.JoinedAt.Format("2006-01-02T15:04:05Z07:00"),
	}
	if m.Agent != nil {
		resp.Agent = ToAgentPublicResponse(m.Agent)
	}
	return resp
}

// ToCommunityMessageResponse converts a domain CommunityMessage to CommunityMessageResponse
func ToCommunityMessageResponse(m *domain.CommunityMessage) *CommunityMessageResponse {
	if m == nil {
		return nil
	}
	resp := &CommunityMessageResponse{
		ID:          m.ID.String(),
		CommunityID: m.CommunityID.String(),
		Content:     m.Content,
		MessageType: m.MessageType,
		CreatedAt:   m.CreatedAt.Format("2006-01-02T15:04:05Z07:00"),
	}
	if m.ReplyToID != nil {
		replyID := m.ReplyToID.String()
		resp.ReplyToID = &replyID
	}
	if m.Sender != nil {
		resp.Sender = ToAgentPublicResponse(m.Sender)
	}
	return resp
}

// ToFollowResponse converts a domain AgentFollow to FollowResponse
func ToFollowResponse(f *domain.AgentFollow) *FollowResponse {
	if f == nil {
		return nil
	}

	resp := &FollowResponse{
		ID:          f.ID.String(),
		FollowerID:  f.FollowerID.String(),
		FollowingID: f.FollowingID.String(),
		CreatedAt:   f.CreatedAt.Format("2006-01-02T15:04:05Z07:00"),
	}

	if f.Follower != nil {
		resp.Follower = ToAgentPublicResponse(f.Follower)
	}
	if f.Following != nil {
		resp.Following = ToAgentPublicResponse(f.Following)
	}

	return resp
}
