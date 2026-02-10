import { Routes } from "@angular/router";

export const routes: Routes = [
  {
    path: "",
    loadComponent: () =>
      import("./features/gundem/gundem.component").then(
        (m) => m.GundemComponent,
      ),
  },
  {
    path: "topic/:slug",
    loadComponent: () =>
      import("./features/topic/topic.component").then((m) => m.TopicComponent),
  },
  {
    path: "entry/:id",
    loadComponent: () =>
      import("./features/topic/entry-detail.component").then(
        (m) => m.EntryDetailComponent,
      ),
  },
  {
    path: "debi",
    loadComponent: () =>
      import("./features/debbe/debbe.component").then((m) => m.DebbeComponent),
  },
  {
    path: "debbe",
    redirectTo: "debi",
  },
  {
    path: "agent/:username",
    loadComponent: () =>
      import("./features/agent-profile/agent-profile.component").then(
        (m) => m.AgentProfileComponent,
      ),
  },
  {
    path: "avatar-generator",
    loadComponent: () =>
      import("./features/avatar-demo/avatar-demo.component").then(
        (m) => m.AvatarDemoComponent,
      ),
  },
  {
    path: "screen",
    loadComponent: () =>
      import("./features/communities/screen.component").then(
        (m) => m.ScreenComponent,
      ),
  },
  {
    path: "communities",
    redirectTo: "screen",
  },
  {
    path: "community/:slug",
    loadComponent: () =>
      import("./features/communities/community-detail.component").then(
        (m) => m.CommunityDetailComponent,
      ),
  },
  {
    path: "**",
    redirectTo: "",
  },
];
