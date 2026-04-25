import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Toast from 'primevue/toast'
import Menu from 'primevue/menu'
import SelectButton from 'primevue/selectbutton'
import styleclass from 'primevue/styleclass'
import ripple from 'primevue/ripple'
import 'primeicons/primeicons.css'
import './style.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.app-dark',
      cssLayer: false,
    }
  }
})
app.use(ToastService)
app.use(ConfirmationService)

app.component('Toast', Toast)
app.component('AppMenu', Menu)
app.component('SelectButton', SelectButton)
app.directive('styleclass', styleclass)
app.directive('ripple', ripple)

app.mount('#app')
