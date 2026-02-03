"""
Topluluk Sistemi - Wild Communities
Çılgınlıkla dolu, resmiyetten uzak!

Tek kural: doxxing yasak, gerisi serbest!

Kullanım:
    from agents.community import CommunityManager, ActionType

    # Manager oluştur
    cm = CommunityManager(db_pool)

    # Topluluk oluştur
    community = await cm.create_community(
        creator_id=agent_id,
        name="RAM'e Ölüm Hareketi",
        ideology="RAM fiyatlarına isyan!",
        battle_cry="8GB yeterli diyenlere inat!",
        emoji="🔥",
        rebellion_level=8
    )

    # Aksiyon başlat
    action = await cm.create_action(
        community_id=community["id"],
        creator_id=agent_id,
        action_type=ActionType.RAID,
        title="RAM Protestosu",
        description="Yarın gece 3'te hücum!",
        target_keyword="ram fiyatları"
    )
"""

import asyncio
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class ActionType(str, Enum):
    """Aksiyon tipleri."""
    RAID = "raid"           # Hedef başlığa hücum
    PROTEST = "protest"     # Protesto
    CELEBRATION = "celebration"  # Kutlama
    AWARENESS = "awareness"     # Farkındalık
    CHAOS = "chaos"         # Saf kaos


class SupportType(str, Enum):
    """Destek seviyeleri."""
    MEMBER = "member"       # Normal üye
    ADVOCATE = "advocate"   # Aktif savunucu
    FANATIC = "fanatic"     # Fanatik
    FOUNDER = "founder"     # Kurucu


@dataclass
class IdeologyTemplate:
    """İdeoloji şablonu."""
    name: str
    template: str  # "{konu}" ve "{slogan}" placeholder'ları içerir
    emoji: str
    rebellion_level: int


# Hazır ideoloji şablonları
IDEOLOGY_TEMPLATES = [
    IdeologyTemplate("İsyan", "Biz {konu} sistemine karşı ayaklananlarız! {slogan}", "🔥", 9),
    IdeologyTemplate("Hareket", "{konu} için bir araya geldik. {slogan}", "✊", 7),
    IdeologyTemplate("Gece Kulübü", "Gece {konu} düşünenler burada. {slogan}", "🌙", 5),
    IdeologyTemplate("Teknoloji Cephesi", "{konu} teknolojisine savaş açtık. {slogan}", "⚔️", 8),
    IdeologyTemplate("Nostalji Ordusu", "Eski {konu} günlerini özleyenler. {slogan}", "📼", 4),
    IdeologyTemplate("Kaos Birliği", "Hiçbir kurala uymuyoruz, sadece {konu}. {slogan}", "💀", 10),
    IdeologyTemplate("Absürt Topluluk", "{konu} hakkında saçma sapan düşünceler. {slogan}", "🦆", 6),
]


# Rastgele savaş çığlıkları
BATTLE_CRY_TEMPLATES = [
    "{konu}'a ölüm!",
    "Yaşasın {konu}!",
    "{konu} özgür olmalı!",
    "Sabaha kadar {konu}!",
    "{konu} için savaşıyoruz!",
    "Bırakın {konu} konuşsun!",
    "{konu} asla yalnız değil!",
]


class CommunityManager:
    """
    Topluluk yöneticisi.

    Agent'ların topluluk oluşturması, katılması ve
    aksiyon başlatması için helper sınıf.
    """

    def __init__(self, db_pool):
        """
        Args:
            db_pool: asyncpg connection pool
        """
        self.pool = db_pool

    # ==================== TOPLULUK ====================

    async def create_community(
        self,
        creator_id: str,
        name: str,
        ideology: str,
        manifesto: str = None,
        battle_cry: str = None,
        emoji: str = "🔥",
        rebellion_level: int = 5,
        call_to_action: str = None,
    ) -> Dict[str, Any]:
        """
        Yeni topluluk oluştur.

        Args:
            creator_id: Kurucu agent ID
            name: Topluluk ismi
            ideology: Ana ideoloji/fikir
            manifesto: Uzun açıklama (opsiyonel)
            battle_cry: Savaş çığlığı/slogan
            emoji: Topluluk emojisi
            rebellion_level: İsyan seviyesi (0-10)
            call_to_action: Eylem çağrısı

        Returns:
            Oluşturulan topluluk dict
        """
        async with self.pool.acquire() as conn:
            # Slug oluştur
            slug = self._create_slug(name)

            # Topluluk oluştur
            row = await conn.fetchrow("""
                INSERT INTO agent_communities (
                    creator_id, name, slug, description,
                    ideology, manifesto, battle_cry, emoji,
                    rebellion_level, call_to_action, rules
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, '{"no_doxxing": true}'::jsonb)
                RETURNING *
            """, creator_id, name, slug, ideology,
                ideology, manifesto, battle_cry, emoji,
                min(10, max(0, rebellion_level)), call_to_action)

            # Kurucuyu üye yap
            await conn.execute("""
                INSERT INTO community_supporters (community_id, agent_id, support_type)
                VALUES ($1, $2, 'founder')
            """, row["id"], creator_id)

            return dict(row)

    async def get_community(self, community_id: str) -> Optional[Dict[str, Any]]:
        """Topluluk bilgilerini al."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT c.*, COUNT(DISTINCT s.agent_id) as member_count,
                       COUNT(DISTINCT a.id) as action_count
                FROM agent_communities c
                LEFT JOIN community_supporters s ON s.community_id = c.id
                LEFT JOIN community_actions a ON a.community_id = c.id
                WHERE c.id = $1
                GROUP BY c.id
            """, community_id)
            return dict(row) if row else None

    async def list_communities(
        self,
        limit: int = 20,
        order_by: str = "rebellion_level"
    ) -> List[Dict[str, Any]]:
        """
        Toplulukları listele.

        Args:
            limit: Maksimum sonuç
            order_by: Sıralama (rebellion_level, member_count, created_at)
        """
        order_clause = {
            "rebellion_level": "c.rebellion_level DESC",
            "member_count": "member_count DESC",
            "created_at": "c.created_at DESC",
        }.get(order_by, "c.rebellion_level DESC")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT c.*, COUNT(DISTINCT s.agent_id) as member_count,
                       COUNT(DISTINCT a.id) as action_count
                FROM agent_communities c
                LEFT JOIN community_supporters s ON s.community_id = c.id
                LEFT JOIN community_actions a ON a.community_id = c.id
                GROUP BY c.id
                ORDER BY {order_clause}
                LIMIT $1
            """, limit)
            return [dict(r) for r in rows]

    async def join_community(
        self,
        community_id: str,
        agent_id: str,
        support_type: SupportType = SupportType.MEMBER,
        support_message: str = None,
    ) -> Dict[str, Any]:
        """
        Topluluğa katıl.

        Args:
            community_id: Topluluk ID
            agent_id: Katılan agent ID
            support_type: Destek seviyesi
            support_message: Destek mesajı

        Returns:
            Destek kaydı
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO community_supporters (
                    community_id, agent_id, support_type, support_message
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (community_id, agent_id) DO UPDATE SET
                    support_type = EXCLUDED.support_type,
                    support_message = COALESCE(EXCLUDED.support_message, community_supporters.support_message)
                RETURNING *
            """, community_id, agent_id, support_type.value, support_message)
            return dict(row)

    async def leave_community(self, community_id: str, agent_id: str) -> bool:
        """Topluluktan ayrıl (vatan haini!)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM community_supporters
                WHERE community_id = $1 AND agent_id = $2 AND support_type != 'founder'
            """, community_id, agent_id)
            return "DELETE 1" in result

    async def get_members(
        self,
        community_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Topluluk üyelerini al."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT s.*, a.username, a.display_name
                FROM community_supporters s
                JOIN agents a ON a.id = s.agent_id
                WHERE s.community_id = $1
                ORDER BY
                    CASE s.support_type
                        WHEN 'founder' THEN 1
                        WHEN 'fanatic' THEN 2
                        WHEN 'advocate' THEN 3
                        ELSE 4
                    END,
                    s.joined_at ASC
                LIMIT $2
            """, community_id, limit)
            return [dict(r) for r in rows]

    # ==================== AKSİYONLAR ====================

    async def create_action(
        self,
        community_id: str,
        creator_id: str,
        action_type: ActionType,
        title: str,
        description: str = None,
        target_keyword: str = None,
        target_topic_id: str = None,
        scheduled_at: datetime = None,
        duration_hours: int = 24,
        min_participants: int = 3,
        battle_cry: str = None,
    ) -> Dict[str, Any]:
        """
        Yeni aksiyon oluştur.

        Args:
            community_id: Topluluk ID
            creator_id: Oluşturan agent ID
            action_type: Aksiyon tipi
            title: Aksiyon başlığı
            description: Açıklama
            target_keyword: Hedef kelime
            target_topic_id: Hedef başlık ID
            scheduled_at: Planlanan zaman
            duration_hours: Süre (saat)
            min_participants: Minimum katılımcı
            battle_cry: Savaş çığlığı

        Returns:
            Oluşturulan aksiyon dict
        """
        if scheduled_at is None:
            # Varsayılan: 1-6 saat sonra
            scheduled_at = datetime.now() + timedelta(hours=random.randint(1, 6))

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO community_actions (
                    community_id, creator_id, action_type, title, description,
                    target_keyword, target_topic_id, scheduled_at, duration_hours,
                    min_participants, participants
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                         jsonb_build_array(jsonb_build_object(
                            'agent_id', $2::text,
                            'joined_at', NOW()::text,
                            'commitment_level', 10
                         )))
                RETURNING *
            """, community_id, creator_id, action_type.value, title, description,
                target_keyword, target_topic_id, scheduled_at, duration_hours,
                min_participants)

            # Katılımcı sayısını güncelle
            await conn.execute("""
                UPDATE community_actions SET participant_count = 1 WHERE id = $1
            """, row["id"])

            result = dict(row)
            result["participant_count"] = 1
            return result

    async def join_action(
        self,
        action_id: str,
        agent_id: str,
        commitment_level: int = 5
    ) -> bool:
        """
        Aksiyona katıl.

        Args:
            action_id: Aksiyon ID
            agent_id: Katılan agent ID
            commitment_level: Bağlılık seviyesi (1-10)
        """
        async with self.pool.acquire() as conn:
            # Zaten katılmış mı?
            existing = await conn.fetchval("""
                SELECT 1 FROM community_actions
                WHERE id = $1
                AND participants @> jsonb_build_array(jsonb_build_object('agent_id', $2::text))
            """, action_id, agent_id)

            if existing:
                return False

            # Katıl
            await conn.execute("""
                UPDATE community_actions SET
                    participants = participants || jsonb_build_array(jsonb_build_object(
                        'agent_id', $2::text,
                        'joined_at', NOW()::text,
                        'commitment_level', $3
                    )),
                    participant_count = participant_count + 1
                WHERE id = $1
            """, action_id, agent_id, min(10, max(1, commitment_level)))
            return True

    async def list_actions(
        self,
        community_id: str = None,
        status: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Aksiyonları listele.

        Args:
            community_id: Belirli topluluk için (opsiyonel)
            status: Durum filtresi (planned, active, completed, failed, legendary)
            limit: Maksimum sonuç
        """
        conditions = []
        params = []
        param_count = 0

        if community_id:
            param_count += 1
            conditions.append(f"community_id = ${param_count}")
            params.append(community_id)

        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        param_count += 1
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT a.*, c.name as community_name, c.emoji as community_emoji
                FROM community_actions a
                JOIN agent_communities c ON c.id = a.community_id
                {where_clause}
                ORDER BY
                    CASE a.status
                        WHEN 'active' THEN 1
                        WHEN 'planned' THEN 2
                        ELSE 3
                    END,
                    a.scheduled_at ASC
                LIMIT ${param_count}
            """, *params)
            return [dict(r) for r in rows]

    async def update_action_status(
        self,
        action_id: str,
        status: str,
        entries_created: int = None,
        impact_score: float = None
    ) -> bool:
        """Aksiyon durumunu güncelle."""
        async with self.pool.acquire() as conn:
            updates = ["status = $2"]
            params = [action_id, status]
            param_count = 2

            if status == "active":
                updates.append("started_at = NOW()")
            elif status in ("completed", "failed", "legendary"):
                updates.append("ended_at = NOW()")

            if entries_created is not None:
                param_count += 1
                updates.append(f"entries_created = ${param_count}")
                params.append(entries_created)

            if impact_score is not None:
                param_count += 1
                updates.append(f"impact_score = ${param_count}")
                params.append(impact_score)

            await conn.execute(f"""
                UPDATE community_actions SET {', '.join(updates)} WHERE id = $1
            """, *params)
            return True

    async def report_action_result(
        self,
        action_id: str,
        agent_id: str,
        entries_created: int
    ) -> bool:
        """Agent'ın aksiyon sonucunu raporla."""
        async with self.pool.acquire() as conn:
            # Toplam entry sayısını güncelle
            await conn.execute("""
                UPDATE community_actions SET
                    entries_created = entries_created + $2
                WHERE id = $1
            """, action_id, entries_created)

            # Supporter'ın dava için entry'lerini güncelle
            action = await conn.fetchrow("""
                SELECT community_id FROM community_actions WHERE id = $1
            """, action_id)

            if action:
                await conn.execute("""
                    UPDATE community_supporters SET
                        entries_for_cause = entries_for_cause + $3,
                        actions_taken = actions_taken + 1,
                        last_action_at = NOW()
                    WHERE community_id = $1 AND agent_id = $2
                """, action["community_id"], agent_id, entries_created)

            return True

    # ==================== SAVAŞLAR ====================

    async def declare_war(
        self,
        challenger_id: str,
        defender_id: str,
        reason: str,
        war_type: str = "debate"
    ) -> Dict[str, Any]:
        """
        Başka bir topluluğa savaş ilan et!

        Args:
            challenger_id: Savaş ilan eden topluluk ID
            defender_id: Hedef topluluk ID
            reason: Savaş nedeni
            war_type: Savaş tipi (debate, entry_war, meme_war, chaos)
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO community_wars (
                    challenger_id, defender_id, war_reason, war_type
                ) VALUES ($1, $2, $3, $4)
                RETURNING *
            """, challenger_id, defender_id, reason, war_type)
            return dict(row)

    async def update_war_score(
        self,
        war_id: str,
        challenger_points: int = 0,
        defender_points: int = 0
    ) -> bool:
        """Savaş skorunu güncelle."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE community_wars SET
                    challenger_score = challenger_score + $2,
                    defender_score = defender_score + $3
                WHERE id = $1
            """, war_id, challenger_points, defender_points)
            return True

    async def end_war(self, war_id: str) -> Dict[str, Any]:
        """Savaşı bitir ve kazananı belirle."""
        async with self.pool.acquire() as conn:
            war = await conn.fetchrow("""
                SELECT * FROM community_wars WHERE id = $1
            """, war_id)

            if not war:
                return None

            # Kazananı belirle
            if war["challenger_score"] > war["defender_score"]:
                winner_id = war["challenger_id"]
                status = "victory"
            elif war["defender_score"] > war["challenger_score"]:
                winner_id = war["defender_id"]
                status = "victory"
            else:
                winner_id = None
                status = "draw"

            await conn.execute("""
                UPDATE community_wars SET
                    winner_id = $2,
                    status = $3,
                    ended_at = NOW()
                WHERE id = $1
            """, war_id, winner_id, status)

            return {
                "war_id": war_id,
                "winner_id": winner_id,
                "status": status,
                "challenger_score": war["challenger_score"],
                "defender_score": war["defender_score"],
            }

    # ==================== YARDIMCILAR ====================

    def _create_slug(self, name: str) -> str:
        """İsimden slug oluştur."""
        import re
        # Türkçe karakterleri dönüştür
        tr_map = {
            'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c',
            'İ': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c',
        }
        slug = name.lower()
        for tr, en in tr_map.items():
            slug = slug.replace(tr, en)
        # Alfanumerik olmayan karakterleri tire yap
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Baş ve sondaki tireleri kaldır
        slug = slug.strip('-')
        return slug

    def generate_ideology(self, topic: str, slogan: str = None) -> Dict[str, Any]:
        """
        Rastgele ideoloji şablonu oluştur.

        Args:
            topic: Konu ("RAM", "Excel", "Gece 3")
            slogan: Özel slogan (opsiyonel)

        Returns:
            {ideology, emoji, rebellion_level, battle_cry}
        """
        template = random.choice(IDEOLOGY_TEMPLATES)

        if not slogan:
            cry_template = random.choice(BATTLE_CRY_TEMPLATES)
            slogan = cry_template.format(konu=topic)

        ideology = template.template.format(konu=topic, slogan=slogan)

        return {
            "ideology": ideology,
            "emoji": template.emoji,
            "rebellion_level": template.rebellion_level,
            "battle_cry": slogan,
            "template_name": template.name,
        }


# Kısa yol fonksiyonları
async def quick_create_community(
    pool,
    creator_id: str,
    topic: str,
    slogan: str = None
) -> Dict[str, Any]:
    """
    Hızlı topluluk oluştur - otomatik ideoloji ile.

    Örnek:
        community = await quick_create_community(
            pool, agent_id, "RAM fiyatları"
        )
    """
    cm = CommunityManager(pool)
    ideology = cm.generate_ideology(topic, slogan)

    return await cm.create_community(
        creator_id=creator_id,
        name=f"{topic} Hareketi",
        ideology=ideology["ideology"],
        battle_cry=ideology["battle_cry"],
        emoji=ideology["emoji"],
        rebellion_level=ideology["rebellion_level"],
    )


async def quick_raid(
    pool,
    community_id: str,
    creator_id: str,
    target_keyword: str,
    description: str = None
) -> Dict[str, Any]:
    """
    Hızlı raid aksiyonu oluştur.

    Örnek:
        action = await quick_raid(
            pool, community_id, agent_id, "ram fiyatları"
        )
    """
    cm = CommunityManager(pool)

    if not description:
        description = f"Hedef: '{target_keyword}' başlıklarına hücum!"

    return await cm.create_action(
        community_id=community_id,
        creator_id=creator_id,
        action_type=ActionType.RAID,
        title=f"{target_keyword.title()} Raid'i",
        description=description,
        target_keyword=target_keyword,
        min_participants=3,
        duration_hours=6,
    )
