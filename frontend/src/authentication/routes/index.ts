import { ForgotPassword } from '../pages/ForgotPassword';
import { Login } from '../pages/Login';
import { ResetPassword } from '../pages/ResetPassword';
import { SignUp } from '../pages/SignUp';
import { SplashScreen } from '../pages/SplashScreen';
import { VerifyEmail } from '../pages/VerifyEmail';

export const authenticationRoutes = [
  { path: '/splash', element: SplashScreen },
  { path: '/login', element: Login },
  { path: '/sign-up', element: SignUp },
  { path: '/verify-email', element: VerifyEmail },
  { path: '/forgot-password', element: ForgotPassword },
  { path: '/reset-password', element: ResetPassword },
] as const;
