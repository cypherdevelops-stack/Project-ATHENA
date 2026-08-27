import { ForgotPassword } from '../pages/ForgotPassword';
import { Login } from '../pages/Login';
import { SignUp } from '../pages/SignUp';
import { SplashScreen } from '../pages/SplashScreen';

export const authenticationRoutes = [
  { path: '/splash', element: SplashScreen },
  { path: '/login', element: Login },
  { path: '/sign-up', element: SignUp },
  { path: '/forgot-password', element: ForgotPassword },
] as const;
