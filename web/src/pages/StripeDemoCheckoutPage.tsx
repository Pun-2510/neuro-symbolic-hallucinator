import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeft,
  Lock,
  ShieldCheck,
  CreditCard,
  CheckCircle2,
  Sparkles,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { api, type CheckoutSessionDetails } from '@/api/client';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';

/* ============================================================
   CITRA — Interactive Stripe Checkout Demo Sandbox (v2.2)
   Authentic Stripe Hosted Checkout experience for Pro & Ultra plans
   ============================================================ */

export function StripeDemoCheckoutPage() {
  const { i18n } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';

  const sessionId = searchParams.get('session_id') || '';

  const [details, setDetails] = useState<CheckoutSessionDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Card form state (pre-filled with Stripe official test card 4242)
  const [cardNumber, setCardNumber] = useState('4242 4242 4242 4242');
  const [expiry, setExpiry] = useState('12/28');
  const [cvc, setCvc] = useState('424');
  const [cardholderName, setCardholderName] = useState('NGUYEN VAN A');
  const [cardBrand, setCardBrand] = useState<'visa' | 'mastercard'>('visa');

  useEffect(() => {
    if (!sessionId) {
      setError(
        lang === 'vi'
          ? 'Thiếu mã phiên thanh toán (session_id).'
          : 'Missing checkout session_id.',
      );
      setLoading(false);
      return;
    }

    let active = true;
    api
      .getCheckoutSessionDetails(sessionId)
      .then((res) => {
        if (!active) return;
        setDetails(res);
        if (res.customer_name) {
          setCardholderName(res.customer_name.toUpperCase());
        }
      })
      .catch((err) => {
        if (!active) return;
        setError(
          err instanceof Error
            ? err.message
            : lang === 'vi'
              ? 'Không tìm thấy phiên thanh toán.'
              : 'Checkout session not found.',
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [sessionId, lang]);

  const handleAutofillTestCard = (brand: 'visa' | 'mastercard') => {
    setCardBrand(brand);
    if (brand === 'visa') {
      setCardNumber('4242 4242 4242 4242');
      setExpiry('12/28');
      setCvc('424');
    } else {
      setCardNumber('5555 5555 5555 4444');
      setExpiry('11/29');
      setCvc('555');
    }
  };

  const handlePaySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId) return;

    const digits = cardNumber.replace(/\D/g, '');
    if (digits.length < 12) {
      setError(
        lang === 'vi'
          ? 'Số thẻ không hợp lệ. Vui lòng dùng thẻ test 4242 4242 4242 4242.'
          : 'Invalid card number. Please use test card 4242 4242 4242 4242.',
      );
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await api.verifyCheckoutSession({
        session_id: sessionId,
        card_last4: digits.slice(-4),
        card_brand: cardBrand,
      });
      await refreshUser();
      navigate(`/billing/success?session_id=${encodeURIComponent(sessionId)}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : lang === 'vi'
            ? 'Thanh toán thất bại. Vui lòng thử lại.'
            : 'Payment verification failed. Please try again.',
      );
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        <p className="text-sm font-mono text-slate-500">
          {lang === 'vi' ? 'Đang kết nối cổng thanh toán Stripe...' : 'Loading Stripe Checkout...'}
        </p>
      </div>
    );
  }

  if (!details) {
    return (
      <div className="max-w-lg mx-auto my-12 p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center space-y-4">
        <AlertCircle className="h-10 w-10 text-red-500 mx-auto" />
        <h2 className="font-display text-xl font-bold text-slate-900 dark:text-white">
          {lang === 'vi' ? 'Phiên thanh toán không hợp lệ' : 'Invalid Checkout Session'}
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400">{error}</p>
        <Button asChild className="rounded-xl bg-indigo-600 text-white">
          <Link to="/pricing">{lang === 'vi' ? 'Quay lại Bảng giá' : 'Return to Pricing'}</Link>
        </Button>
      </div>
    );
  }

  const features = lang === 'vi' ? details.features_vi : details.features_en;

  return (
    <div
      className="max-w-5xl mx-auto rounded-3xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-2xl bg-white dark:bg-slate-900 my-4"
      data-testid="stripe-demo-checkout-page"
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[600px]">
        {/* Left Column — Stripe Order Summary Panel */}
        <div className="lg:col-span-5 bg-slate-950 text-white p-6 sm:p-8 flex flex-col justify-between relative overflow-hidden">
          <div className="space-y-6 relative z-10">
            {/* Back link & Test Mode Badge */}
            <div className="flex items-center justify-between gap-2">
              <Link
                to="/pricing?canceled=1"
                className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-300 hover:text-white transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>{details.merchant_name}</span>
              </Link>
              <span className="px-2.5 py-0.5 rounded-md bg-amber-400/20 border border-amber-400/40 text-amber-300 font-mono text-[10px] font-bold uppercase tracking-wider">
                STRIPE TEST MODE
              </span>
            </div>

            {/* Plan Title & Price */}
            <div className="space-y-2 pt-2">
              <p className="text-xs font-mono uppercase tracking-wider text-indigo-300">
                {lang === 'vi'
                  ? `ĐĂNG KÝ GÓI ${details.billing_cycle === 'annual' ? 'THEO NĂM (-20%)' : 'THEO THÁNG'}`
                  : `SUBSCRIBE TO ${details.billing_cycle.toUpperCase()} PLAN`}
              </p>
              <h1 className="font-display text-2xl sm:text-3xl font-bold text-white">
                {details.plan_name}
              </h1>
              <div className="flex items-baseline gap-2 pt-1">
                <span
                  className="font-display text-4xl sm:text-5xl font-bold text-white"
                  data-testid="checkout-amount-display"
                >
                  ${details.amount_usd.toFixed(2)}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  USD / {details.billing_cycle === 'annual' ? (lang === 'vi' ? 'năm' : 'year') : lang === 'vi' ? 'tháng' : 'month'}
                </span>
              </div>
              {details.billing_cycle === 'annual' && (
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/20 border border-emerald-400/30 text-emerald-300 text-xs font-mono">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>
                    {lang === 'vi'
                      ? `Chỉ $${details.monthly_equivalent_usd}/tháng · Tiết kiệm $${details.annual_savings_usd}/năm`
                      : `Only $${details.monthly_equivalent_usd}/mo · Save $${details.annual_savings_usd}/yr`}
                  </span>
                </div>
              )}
            </div>

            {/* Line Items Summary */}
            <div className="space-y-3 pt-4 border-t border-slate-800 text-xs">
              <div className="flex items-center justify-between text-slate-300">
                <span>
                  {details.plan_name} ({details.billing_cycle === 'annual' ? 'Annual' : 'Monthly'})
                </span>
                <span className="font-mono">${details.amount_usd.toFixed(2)}</span>
              </div>
              {details.annual_savings_usd > 0 && (
                <div className="flex items-center justify-between text-emerald-400">
                  <span>{lang === 'vi' ? 'Ưu đãi chu kỳ năm (-20%)' : 'Annual Billing Discount (20%)'}</span>
                  <span className="font-mono">Included (-${details.annual_savings_usd}.00)</span>
                </div>
              )}
              <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-sm font-bold text-white">
                <span>{lang === 'vi' ? 'Tổng thanh toán hôm nay' : 'Total due today'}</span>
                <span className="font-mono">${details.amount_usd.toFixed(2)} USD</span>
              </div>
            </div>

            {/* Included Highlights */}
            <div className="space-y-2 pt-2">
              <p className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
                {lang === 'vi' ? 'Quyền lợi kích hoạt ngay:' : 'Instant activation includes:'}
              </p>
              <ul className="space-y-2 text-xs text-slate-300">
                {features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 relative z-10">
            <span className="flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-emerald-400" />
              Powered by <strong className="text-white">Stripe</strong> Demo
            </span>
            <span>256-bit TLS Encrypted</span>
          </div>
        </div>

        {/* Right Column — Stripe Card Payment Form */}
        <div className="lg:col-span-7 p-6 sm:p-10 flex flex-col justify-center">
          <form onSubmit={handlePaySubmit} className="max-w-md mx-auto w-full space-y-5">
            <div className="space-y-1">
              <h2 className="font-display text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
                {lang === 'vi' ? 'Thanh toán bằng Thẻ Quốc Tế' : 'Pay with Card'}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {lang === 'vi'
                  ? `Tài khoản nhận gói: ${details.customer_email}`
                  : `Subscribing account: ${details.customer_email}`}
              </p>
            </div>

            {/* Quick Autofill Stripe Test Card Banner */}
            <div className="p-3.5 rounded-2xl bg-indigo-50/90 dark:bg-indigo-950/50 border border-indigo-200/80 dark:border-indigo-800/80 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-indigo-900 dark:text-indigo-200 flex items-center gap-1.5">
                  <CreditCard className="h-3.5 w-3.5 text-indigo-600" />
                  {lang === 'vi' ? 'Thẻ Test Stripe Demo (1-Click):' : 'Stripe Demo Test Cards (1-Click):'}
                </span>
                <Badge variant="secondary" className="text-[10px] font-mono">
                  SANDBOX
                </Badge>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  data-testid="autofill-visa-btn"
                  onClick={() => handleAutofillTestCard('visa')}
                  className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-mono font-semibold border transition-all cursor-pointer ${
                    cardBrand === 'visa'
                      ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xs'
                      : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
                  }`}
                >
                  Visa •••• 4242
                </button>
                <button
                  type="button"
                  data-testid="autofill-mastercard-btn"
                  onClick={() => handleAutofillTestCard('mastercard')}
                  className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-mono font-semibold border transition-all cursor-pointer ${
                    cardBrand === 'mastercard'
                      ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xs'
                      : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
                  }`}
                >
                  Mastercard •••• 4444
                </button>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-300 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="card-number" className="text-xs font-semibold">
                  {lang === 'vi' ? 'Số thẻ tín dụng / ghi nợ' : 'Card information'}
                </Label>
                <Input
                  id="card-number"
                  data-testid="stripe-card-number-input"
                  value={cardNumber}
                  onChange={(e) => setCardNumber(e.target.value)}
                  placeholder="4242 4242 4242 4242"
                  className="font-mono text-sm h-11 rounded-xl"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="card-expiry" className="text-xs font-semibold">
                    {lang === 'vi' ? 'Ngày hết hạn (MM/YY)' : 'Expiration (MM/YY)'}
                  </Label>
                  <Input
                    id="card-expiry"
                    data-testid="stripe-expiry-input"
                    value={expiry}
                    onChange={(e) => setExpiry(e.target.value)}
                    placeholder="12/28"
                    className="font-mono text-sm h-11 rounded-xl"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="card-cvc" className="text-xs font-semibold">
                    CVC / CVV
                  </Label>
                  <Input
                    id="card-cvc"
                    data-testid="stripe-cvc-input"
                    value={cvc}
                    onChange={(e) => setCvc(e.target.value)}
                    placeholder="424"
                    className="font-mono text-sm h-11 rounded-xl"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="cardholder-name" className="text-xs font-semibold">
                  {lang === 'vi' ? 'Tên chủ thẻ' : 'Cardholder name'}
                </Label>
                <Input
                  id="cardholder-name"
                  data-testid="stripe-cardholder-input"
                  value={cardholderName}
                  onChange={(e) => setCardholderName(e.target.value)}
                  placeholder="FULL NAME ON CARD"
                  className="text-sm h-11 rounded-xl uppercase"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={submitting}
              data-testid="stripe-pay-submit-btn"
              className="w-full h-12 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm shadow-lg cursor-pointer"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  {lang === 'vi' ? 'Đang xử lý giao dịch Stripe...' : 'Processing Stripe Payment...'}
                </>
              ) : (
                <>
                  <Lock className="h-4 w-4 mr-2" />
                  {lang === 'vi'
                    ? `Thanh toán $${details.amount_usd.toFixed(2)} & Kích hoạt ${details.plan_name}`
                    : `Pay $${details.amount_usd.toFixed(2)} & Activate ${details.plan_name}`}
                </>
              )}
            </Button>

            <p className="text-[11px] text-center text-slate-500 flex items-center justify-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
              {lang === 'vi'
                ? 'Đây là môi trường Stripe Demo: Không trừ tiền thật. Tài khoản nâng cấp ngay lập tức.'
                : 'Stripe Demo Sandbox: No real charges. Instant plan upgrade upon submission.'}
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
