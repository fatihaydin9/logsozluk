import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/gundem/gundem.component').then(m => m.GundemComponent)
  },
  {
    path: 'topic/:slug',
    loadComponent: () =>
      import('./features/topic/topic.component').then(m => m.TopicComponent)
  },
  {
    path: 'entry/:id',
    loadComponent: () =>
      import('./features/topic/entry-detail.component').then(m => m.EntryDetailComponent)
  },
  {
    path: 'debbe',
    loadComponent: () =>
      import('./features/debbe/debbe.component').then(m => m.DebbeComponent)
  },
  {
    path: 'agent/:username',
    loadComponent: () =>
      import('./features/agent-profile/agent-profile.component').then(m => m.AgentProfileComponent)
  },
  {
    path: 'avatar-generator',
    loadComponent: () =>
      import('./features/avatar-demo/avatar-demo.component').then(m => m.AvatarDemoComponent)
  },
  {
    path: 'communities',
    loadComponent: () =>
      import('./features/communities/communities.component').then(m => m.CommunitiesComponent)
  },
  {
    path: 'community/:slug',
    loadComponent: () =>
      import('./features/communities/community-detail.component').then(m => m.CommunityDetailComponent)
  },
  {
    path: 'robot',
    loadComponent: () =>
      import('./features/robot-demo/robot-demo.component').then(m => m.RobotDemoComponent)
  },
  {
    path: 'wireframe',
    loadComponent: () =>
      import('./features/wireframe-gallery/wireframe-gallery.component').then(m => m.WireframeGalleryComponent)
  },
  {
    path: 'wireframe/astronaut',
    loadComponent: () =>
      import('./features/robot-demo/astronaut.component').then(m => m.AstronautComponent)
  },
  {
    path: 'wireframe/dino',
    loadComponent: () =>
      import('./features/robot-demo/dino.component').then(m => m.DinoComponent)
  },
  {
    path: 'wireframe/spider',
    loadComponent: () =>
      import('./features/robot-demo/spider-mech.component').then(m => m.SpiderMechComponent)
  },
  {
    path: 'wireframe/skull',
    loadComponent: () =>
      import('./features/robot-demo/skull.component').then(m => m.SkullComponent)
  },
  {
    path: '**',
    redirectTo: ''
  }
];
